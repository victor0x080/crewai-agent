import time
import logging
import os
from typing import Optional

try:
    import redis  # type: ignore
except Exception as _e:  # pragma: no cover
    redis = None  # Fallback for environments without redis-py installed


logger = logging.getLogger(__name__)


class OpenAIRateLimiter:
    """Redis-backed global rate limiter for OpenAI usage.

    Coordinates RPM/TPM across all agent processes and enforces a single
    execution lock so only one OpenAI call runs at a time.
    """

    def __init__(
        self,
        redis_client: Optional["redis.Redis"] = None,
        rpm_limit: int = 50,
        tpm_limit: int = 10000,
        max_concurrent: int = 3,  # Allow up to 3 concurrent executions
    ) -> None:
        if redis is None:
            raise RuntimeError("redis package is required for OpenAIRateLimiter")

        self.redis = redis_client or redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,
        )

        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.max_concurrent = max_concurrent

        self.rpm_key_prefix = "openai:rate_limit:rpm"
        self.tpm_key_prefix = "openai:rate_limit:tpm"
        self.quota_error_key = "openai:quota_error:timestamp"
        self.cooldown_seconds = int(os.getenv("OPENAI_COOLDOWN_SECONDS", "300"))
        self.concurrent_lock_key = "openai:concurrent_executions"

        logger.info(
            f"🚦 Rate limiter initialized: {self.rpm_limit} RPM, {self.tpm_limit} TPM, {self.max_concurrent} max concurrent"
        )

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _get_minute_window(self) -> str:
        return time.strftime("%Y%m%d%H%M", time.gmtime())

    def _check_quota_cooldown(self) -> bool:
        try:
            ts = self.redis.get(self.quota_error_key)
            if not ts:
                return False
            # Still within cooldown
            return True
        except Exception as e:
            logger.error(f"RateLimiter: error reading cooldown: {e}")
            return False

    def _check_rpm(self) -> bool:
        key = f"{self.rpm_key_prefix}:{self._get_minute_window()}"
        try:
            current = self.redis.incr(key)
            # expire in 90s to cover minute boundary
            if current == 1:
                self.redis.expire(key, 90)
            allowed = current <= self.rpm_limit
            if not allowed:
                logger.debug(f"RateLimiter: RPM exceeded ({current}/{self.rpm_limit})")
            return allowed
        except Exception as e:
            logger.error(f"RateLimiter: error checking RPM: {e}")
            # Be safe and deny if we cannot verify
            return False

    def _check_tpm(self, estimated_tokens: int) -> bool:
        key = f"{self.tpm_key_prefix}:{self._get_minute_window()}"
        try:
            current = self.redis.incrby(key, max(estimated_tokens, 0))
            if current == estimated_tokens:
                self.redis.expire(key, 90)
            allowed = current <= self.tpm_limit
            if not allowed:
                logger.debug(
                    f"RateLimiter: TPM exceeded ({current}/{self.tpm_limit}) with est={estimated_tokens}"
                )
            return allowed
        except Exception as e:
            logger.error(f"RateLimiter: error checking TPM: {e}")
            return False

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def wait_for_slot(self, estimated_tokens: int = 1000, max_wait: float = 90.0) -> bool:
        """Wait for a rate limit slot and acquire the execution lock.

        Returns True if acquired within max_wait, False otherwise.
        """
        start = time.time()
        lock_key = "openai:execution_lock"

        while time.time() - start < max_wait:
            # Cooldown after hard quota error
            if self._check_quota_cooldown():
                time.sleep(min(5.0, max_wait - (time.time() - start)))
                continue

            # Try to acquire execution slot (allow up to max_concurrent executions)
            # Check current concurrent count
            new_count = None
            try:
                current_count = self.redis.get(self.concurrent_lock_key)
                current_count = int(current_count) if current_count else 0
                
                if current_count >= self.max_concurrent:
                    # Too many concurrent executions, wait
                    time.sleep(0.5)
                    continue
                
                # Increment concurrent count
                new_count = self.redis.incr(self.concurrent_lock_key)
                if new_count == 1:
                    self.redis.expire(self.concurrent_lock_key, 180)  # Expire after 3 minutes
                
                # Also acquire individual execution lock for this agent
                lock_acquired = self.redis.set(f"{lock_key}:{new_count}", "locked", ex=120, nx=True)
                if not lock_acquired:
                    # Failed to acquire individual lock, decrement count
                    self.redis.decr(self.concurrent_lock_key)
                    time.sleep(0.5)
                    continue
                    
            except Exception as e:
                logger.error(f"RateLimiter: error acquiring concurrent slot: {e}")
                if new_count is not None:
                    try:
                        self.redis.decr(self.concurrent_lock_key)
                    except Exception:
                        pass
                time.sleep(0.5)
                continue

            # With slot, verify RPM and TPM windows
            try:
                if not self._check_rpm():
                    # Release slot and individual lock
                    if new_count is not None:
                        self.redis.decr(self.concurrent_lock_key)
                        self.redis.delete(f"{lock_key}:{new_count}")
                    time.sleep(1.5)
                    continue
                if not self._check_tpm(estimated_tokens):
                    # Release slot and individual lock
                    if new_count is not None:
                        self.redis.decr(self.concurrent_lock_key)
                        self.redis.delete(f"{lock_key}:{new_count}")
                    time.sleep(1.5)
                    continue
                logger.info(f"✅ Rate limit slot acquired ({estimated_tokens} est tokens, {new_count}/{self.max_concurrent} concurrent)")
                return True
            except Exception as e:
                logger.error(f"RateLimiter: error checking limits: {e}")
                try:
                    if new_count is not None:
                        self.redis.decr(self.concurrent_lock_key)
                        self.redis.delete(f"{lock_key}:{new_count}")
                except Exception:
                    pass
                time.sleep(1.0)

        logger.warning(f"⏱️ RateLimiter: wait_for_slot timed out after {max_wait}s")
        return False

    def release_execution_lock(self) -> None:
        try:
            # Decrement concurrent count
            count = self.redis.decr(self.concurrent_lock_key)
            if count and count < 0:
                # Reset if it goes negative (shouldn't happen, but safety check)
                self.redis.set(self.concurrent_lock_key, 0)
            
            # Try to delete any individual locks (cleanup)
            for i in range(1, self.max_concurrent + 1):
                try:
                    self.redis.delete(f"openai:execution_lock:{i}")
                except Exception:
                    pass
                    
            logger.debug(f"🔓 Execution lock released (concurrent: {count or 0}/{self.max_concurrent})")
        except Exception as e:
            logger.error(f"RateLimiter: error releasing lock: {e}")

    def record_quota_error(self) -> None:
        try:
            self.redis.set(
                self.quota_error_key,
                str(time.time()),
                ex=self.cooldown_seconds + 10,
            )
            logger.error(
                f"🚫 Quota error recorded, entering cooldown for {self.cooldown_seconds}s"
            )
        except Exception as e:
            logger.error(f"RateLimiter: error recording quota error: {e}")


_rate_limiter: Optional[OpenAIRateLimiter] = None


def get_rate_limiter() -> OpenAIRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        rpm = int(os.getenv("OPENAI_RPM_LIMIT", "50"))
        tpm = int(os.getenv("OPENAI_TPM_LIMIT", "10000"))
        _rate_limiter = OpenAIRateLimiter(rpm_limit=rpm, tpm_limit=tpm)
    return _rate_limiter




