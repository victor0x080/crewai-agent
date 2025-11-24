/**
 * Agent Registry
 * Definitions for RMN (Retail Media Network) agents and MCO agents
 */

export const agentRegistry = [];

// Export utility functions
export function getAgentById(id) {
  return agentRegistry.find(a => a.id === id);
}

export function getAgentsByCategory(category) {
  return agentRegistry.filter(a => a.category === category);
}

export function getAgentsByCapability(capability) {
  return agentRegistry.filter(a => a.capabilities.includes(capability));
}

export function getAllAgentIds() {
  return agentRegistry.map(a => a.id);
}

export function getAgentCount() {
  return agentRegistry.length;
}

// Log registry info on import
console.log(`📦 Agent Registry loaded: ${agentRegistry.length} agents`);
console.log(`   Categories: ${new Set(agentRegistry.map(a => a.category)).size}`);
console.log(`   MCO: ${getAgentsByCategory('mco').length}`);
console.log(`   RMN: ${getAgentsByCategory('rmn').length}`);

