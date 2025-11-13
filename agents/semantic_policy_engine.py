"""
Semantic Policy Engine
Filters CrewAI events based on policies with embeddings, rules, and optional LLM checks.
"""

import hashlib
import json
import re
import time
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import yaml

# --- Minimal embedder interface ------------------------------------------------
class Embedder:
    """Abstract embedder - implement with OpenAI, Cohere, or local model"""
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return list of embedding vectors (same length as texts)."""
        raise NotImplementedError

class OpenAIEmbedder(Embedder):
    """OpenAI embeddings implementation"""
    def __init__(self, client, model="text-embedding-3-small"):
        self.client = client
        self.model = model
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [item.embedding for item in response.data]

def cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors"""
    if not a or not b:
        return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)

# --- Optional LLM check interface ---------------------------------------------
class LLMJudge:
    """LLM-based final arbiter for broadcast decisions"""
    def __init__(self, client):
        self.client = client
    
    def check(self, policy_name: str, payload: Dict[str, Any], prompt: str, **kwargs) -> Dict[str, Any]:
        """Return {"broadcast": bool, "tags": [], "reason": "..."}"""
        try:
            max_tokens = kwargs.get("max_tokens", 120)
            temperature = kwargs.get("temperature", 0.0)
            
            # Build compact prompt
            full_prompt = f"{prompt}\n\nPayload:\n{json.dumps(payload, indent=2)[:1000]}"
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a strict event routing filter. Return only valid JSON."},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "broadcast": result.get("broadcast", False),
                "tags": result.get("tags", []),
                "reason": result.get("reason", "")
            }
            
        except Exception as e:
            print(f"[LLMJudge] Error in check: {e}")
            return {"broadcast": False, "tags": [], "reason": f"error: {str(e)}"}

# --- Policy model --------------------------------------------------------------
@dataclass
class Policy:
    name: str
    topics: List[str]
    when: Dict[str, Any]
    semantics: Dict[str, Any]
    llm_check: Optional[Dict[str, Any]] = None
    novelty: Optional[Dict[str, Any]] = None
    description: str = ""

# --- Engine -------------------------------------------------------------------
class SemanticPolicyEngine:
    """
    Semantic policy engine for filtering CrewAI events.
    
    Combines:
    1. Deterministic rules (cheap, fast)
    2. Embedding similarity (semantic matching)
    3. Optional LLM check (final arbiter)
    4. Deduplication and PII redaction
    """
    
    def __init__(self, cfg: Dict[str, Any], embedder: Embedder, judge: Optional[LLMJudge] = None):
        self.cfg = cfg
        self.embedder = embedder
        self.judge = judge
        self._goal_vecs = {}      # policy_name -> [vectors]
        self._dedupe = {}         # hash -> last_ts
        self._compile_pii()
        self._precompute_goals()
        
        print(f"[SemanticPolicyEngine] Initialized with {len(self._iter_policies())} policies")
    
    @classmethod
    def from_yaml(cls, yaml_path: str, embedder: Embedder, judge: Optional[LLMJudge] = None):
        """Load policies from YAML file"""
        with open(yaml_path, 'r') as f:
            cfg = yaml.safe_load(f)
        return cls(cfg, embedder, judge)
    
    # -------- Public API
    def should_broadcast(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Determine if event should be broadcast based on policies.
        
        Returns:
            None if event should not be broadcast
            Dict with topics, body, and meta if it should be broadcast
        """
        # Global prefilter
        if not self._passes_rules(event):
            return None
        
        # Deep copy and redact
        redacted = self._redact(json.loads(json.dumps(event)))
        
        # Check for duplicates
        if self._is_duplicate(redacted):
            print(f"[SemanticPolicyEngine] Duplicate event dropped: {event.get('type')}")
            return None
        
        decisions = []
        
        # Evaluate each policy
        for pol in self._iter_policies():
            # 1) Deterministic rules
            if not self._rules_match(pol.when, redacted):
                continue
            
            # 2) Embedding similarity
            texts = self._collect_fields(redacted, pol.semantics.get("fields", []))
            if not texts:
                continue
            
            ev_text = "\n".join(texts) or ""
            if not ev_text.strip():
                continue
            
            ev_vec = self.embedder.embed([ev_text])[0]
            sims = [cosine(ev_vec, g) for g in self._goal_vecs[pol.name]]
            score = max(sims) if sims else 0.0
            min_sim = pol.semantics.get("min_similarity", self.cfg["defaults"]["min_similarity"])
            
            if score < min_sim:
                continue
            
            print(f"[SemanticPolicyEngine] Policy '{pol.name}' matched with similarity {score:.3f}")
            
            # 3) Optional novelty check
            if pol.novelty and not self._passes_novelty(pol, redacted):
                print(f"[SemanticPolicyEngine] Policy '{pol.name}' rejected by novelty check")
                continue
            
            # 4) Optional LLM check
            if (pol.llm_check or {}).get("enabled", self.cfg["defaults"]["require_llm_check"]):
                if self.judge:
                    verdict = self.judge.check(pol.name, redacted, pol.llm_check.get("prompt", ""), **pol.llm_check)
                    if not verdict.get("broadcast"):
                        print(f"[SemanticPolicyEngine] Policy '{pol.name}' rejected by LLM check: {verdict.get('reason')}")
                        continue
                    meta = {"policy": pol.name, "similarity": round(score, 3), "llm": verdict}
                else:
                    print(f"[SemanticPolicyEngine] Policy '{pol.name}' requires LLM check but no judge configured")
                    continue
            else:
                meta = {"policy": pol.name, "similarity": round(score, 3)}
            
            # Winner for this policy
            decisions.append({
                "topics": pol.topics,
                "body": redacted,
                "meta": meta
            })
        
        # Return the strongest match (highest similarity) if any
        if not decisions:
            return None
        
        winner = max(decisions, key=lambda d: d["meta"]["similarity"])
        self._mark_duplicate(winner["body"])
        
        print(f"[SemanticPolicyEngine] Broadcasting to {winner['topics']} (policy: {winner['meta']['policy']})")
        return winner
    
    # -------- Internals
    def _iter_policies(self) -> List[Policy]:
        return [Policy(**p) for p in self.cfg.get("policies", [])]
    
    def _passes_rules(self, event: Dict[str, Any]) -> bool:
        """Global cheap checks"""
        # Require minimum fields
        if not event.get("type"):
            return False
        return True
    
    def _rules_match(self, rules: Dict[str, Any], ev: Dict[str, Any]) -> bool:
        """Check if event matches policy rules"""
        t = ev.get("type", "")
        
        # Event type filter
        if "event_types" in rules and not self._match_any(t, rules["event_types"]):
            return False
        
        # Success filter
        if rules.get("require_success") is True and not ev.get("success", True):
            return False
        if rules.get("require_success") is False and ev.get("success", True):
            return False
        
        # Agent filter
        if "agents_allowlist" in rules:
            agent_name = ev.get("agent", {}).get("name", "")
            if not self._match_any(agent_name, rules["agents_allowlist"]):
                return False
        
        # Task filter
        if "tasks_allowlist" in rules:
            task_name = ev.get("task", {}).get("name", "")
            if not self._match_any(task_name, rules["tasks_allowlist"]):
                return False
        
        # Tool filter
        if "tools_allowlist" in rules:
            tool_name = (ev.get("tool") or {}).get("name", "")
            if not self._match_any(tool_name, rules["tools_allowlist"]):
                return False
        
        # Token threshold
        if "min_tokens" in rules:
            tokens = ev.get("metadata", {}).get("tokens", 0)
            if tokens < rules["min_tokens"]:
                return False
        
        return True
    
    def _collect_fields(self, ev: Dict[str, Any], fields: List[str]) -> List[str]:
        """Extract text from specified fields in event"""
        out = []
        for path in fields:
            cur = ev
            for part in path.split("."):
                cur = cur.get(part, {}) if isinstance(cur, dict) else {}
            if isinstance(cur, (str, int, float)):
                out.append(str(cur))
        return out
    
    def _compile_pii(self):
        """Compile PII redaction patterns"""
        self._pii_res = []
        red = (self.cfg.get("defaults", {}).get("redact", {}) or {})
        if red.get("enabled"):
            for p in red.get("pii_patterns", []):
                try:
                    self._pii_res.append(re.compile(p))
                except Exception as e:
                    print(f"[SemanticPolicyEngine] Invalid PII pattern: {p} - {e}")
    
    def _redact(self, obj: Any) -> Any:
        """Recursively redact PII from object"""
        if not self._pii_res:
            return obj
        
        if isinstance(obj, dict):
            return {k: self._redact(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._redact(v) for v in obj]
        if isinstance(obj, str):
            s = obj
            for rgx in self._pii_res:
                s = rgx.sub("[REDACTED]", s)
            return s
        return obj
    
    def _stable_hash(self, ev: Dict[str, Any]) -> str:
        """Generate stable hash for deduplication"""
        key = json.dumps({
            "type": ev.get("type"),
            "agent": ev.get("agent", {}).get("name"),
            "task": ev.get("task", {}).get("name"),
            "output": str(ev.get("output", ""))[:500]  # cap output length
        }, sort_keys=True)
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _is_duplicate(self, ev: Dict[str, Any]) -> bool:
        """Check if event is a duplicate within time window"""
        window = self.cfg["defaults"].get("dedupe_window_seconds", 0)
        if not window:
            return False
        
        h = self._stable_hash(ev)
        last = self._dedupe.get(h)
        return last is not None and (time.time() - last) < window
    
    def _mark_duplicate(self, ev: Dict[str, Any]):
        """Mark event as seen for deduplication"""
        h = self._stable_hash(ev)
        self._dedupe[h] = time.time()
    
    def _passes_novelty(self, pol: Policy, ev: Dict[str, Any]) -> bool:
        """
        Check if event is novel compared to recent history.
        Hook point: integrate with CrewAI memory or external store.
        """
        # TODO: Integrate with CrewAI memory system
        # For now, always pass
        return True
    
    def _match_any(self, value: str, patterns: List[str]) -> bool:
        """Check if value matches any fnmatch pattern"""
        import fnmatch
        return any(fnmatch.fnmatch(value or "", pat) for pat in patterns)
    
    def _precompute_goals(self):
        """Precompute embeddings for all policy goal vectors"""
        print("[SemanticPolicyEngine] Precomputing policy goal embeddings...")
        for pol in self._iter_policies():
            goals = pol.semantics.get("goal_vectors", [])
            if goals:
                try:
                    self._goal_vecs[pol.name] = self.embedder.embed(goals)
                    print(f"  ✓ Policy '{pol.name}': {len(goals)} goal vectors")
                except Exception as e:
                    print(f"  ✗ Policy '{pol.name}': Error embedding goals - {e}")
                    self._goal_vecs[pol.name] = []
            else:
                self._goal_vecs[pol.name] = []
