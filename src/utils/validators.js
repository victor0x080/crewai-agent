/**
 * Input Validators
 * Validates request payloads
 */

export function validateProcessMessageRequest(data) {
  const errors = [];
  
  if (!data) {
    errors.push('Request body is required');
    return { valid: false, errors };
  }
  
  if (!data.message || typeof data.message !== 'string') {
    errors.push('message field is required and must be a string');
  }
  
  if (data.message && data.message.length < 1) {
    errors.push('message cannot be empty');
  }
  
  if (data.message && data.message.length > 10000) {
    errors.push('message is too long (max 10000 characters)');
  }
  
  if (data.conversationId && typeof data.conversationId !== 'string') {
    errors.push('conversationId must be a string');
  }
  
  if (data.context && typeof data.context !== 'object') {
    errors.push('context must be an object');
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}


