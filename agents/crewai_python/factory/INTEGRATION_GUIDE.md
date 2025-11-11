# Integration Guide: CrewAI Agent Factory

This guide shows how to integrate the Agent Factory with the existing orchestration system.

## Architecture Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    Continuous Orchestration Engine               │
│                                                                   │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │ DataTriggerMonitor│────────▶│ TriggerEvent     │              │
│  └──────────────────┘         └──────────────────┘              │
│                                        │                          │
│                                        ▼                          │
│                          ┌──────────────────────┐                │
│                          │ ProactiveAgentSpawner│                │
│                          └──────────────────────┘                │
│                                        │                          │
└────────────────────────────────────────┼──────────────────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────┐
                          │   Agent Registry Lookup  │
                          │   (Static Agents)        │
                          └──────────────────────────┘
                                         │
                                         │ Not Found?
                                         ▼
                          ┌──────────────────────────┐
                          │  CrewAI Agent Factory    │◀─── NEW
                          │  (Dynamic Generation)    │
                          └──────────────────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────┐
                          │  Generated CrewAI Agent  │
                          └──────────────────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────┐
                          │    Agent Execution       │
                          │    (Task + Crew)         │
                          └──────────────────────────┘
```

## Step 1: Modify ProactiveAgentSpawner (TypeScript)

**File:** `src/services/continuous-orchestration/ProactiveAgentSpawner.ts`

Add factory integration:

```typescript
import { spawn } from 'child_process';
import { promisify } from 'util';
import { writeFile, unlink } from 'fs/promises';

export class ProactiveAgentSpawner {
  private agentFactory: any; // Python factory bridge
  
  constructor(config: OrchestrationConfig, eventBus: EventBus) {
    this.config = config;
    this.eventBus = eventBus;
    this.initializeAgentTemplates();
    this.setupEventHandlers();
    
    // NEW: Initialize agent factory bridge
    this.initializeAgentFactory();
  }
  
  private initializeAgentFactory() {
    // Bridge to Python agent factory
    this.agentFactory = {
      generateAgent: async (trigger: TriggerEvent, context: any) => {
        return await this.callPythonAgentFactory(trigger, context);
      }
    };
  }
  
  async spawnAgentsForTrigger(trigger: TriggerEvent): Promise<SpawnedAgent[]> {
    console.log(`🤖 Spawning agents for trigger: ${trigger.type} from ${trigger.source}`);

    try {
      // Determine which agents to spawn based on trigger
      const agentTypes = this.determineAgentTypesForTrigger(trigger);
      
      if (agentTypes.length === 0) {
        console.log(`   No suitable agents found for trigger ${trigger.id}`);
        
        // NEW: Try auto-generation
        console.log(`   🔄 Attempting auto-generation...`);
        const generatedAgent = await this.autoGenerateAgent(trigger);
        
        if (generatedAgent) {
          return [generatedAgent];
        }
        
        return [];
      }

      const spawnedAgents: SpawnedAgent[] = [];

      for (const agentType of agentTypes) {
        try {
          const agent = await this.spawnAgent(agentType, trigger);
          spawnedAgents.push(agent);
          this.activeAgents.set(agent.id, agent);
        } catch (error) {
          console.error(`❌ Failed to spawn agent ${agentType}:`, error);
          
          // NEW: Fallback to auto-generation
          console.log(`   🔄 Falling back to auto-generation...`);
          const generatedAgent = await this.autoGenerateAgent(trigger);
          
          if (generatedAgent) {
            spawnedAgents.push(generatedAgent);
            this.activeAgents.set(generatedAgent.id, generatedAgent);
          }
        }
      }

      return spawnedAgents;

    } catch (error) {
      console.error(`❌ Failed to spawn agents for trigger ${trigger.id}:`, error);
      return [];
    }
  }
  
  // NEW: Auto-generate agent using Python factory
  private async autoGenerateAgent(trigger: TriggerEvent): Promise<SpawnedAgent | null> {
    try {
      const context = await this.getBusinessContext();
      const availableDatasets = this.getAvailableDatasets();
      
      console.log(`🤖 Calling Python Agent Factory...`);
      
      const agentSpec = await this.agentFactory.generateAgent(trigger, {
        ...context,
        available_datasets: availableDatasets
      });
      
      if (!agentSpec) {
        console.error(`❌ Agent factory returned null`);
        return null;
      }
      
      console.log(`✅ Generated agent: ${agentSpec.role}`);
      
      // Create spawned agent record
      const spawnedAgent: SpawnedAgent = {
        id: `dynamic_${Date.now()}_${Math.random().toString(36).substring(7)}`,
        type: 'dynamic',
        name: agentSpec.role,
        status: 'spawning',
        trigger: trigger,
        context: {
          goal: agentSpec.goal,
          backstory: agentSpec.backstory,
          capabilities: agentSpec.capabilities,
          tools: agentSpec.tools
        },
        spawnedAt: new Date().toISOString(),
        pythonAgentId: agentSpec.agent_id
      };
      
      // Execute the Python agent
      await this.executePythonAgent(spawnedAgent, trigger);
      
      return spawnedAgent;
      
    } catch (error) {
      console.error(`❌ Auto-generation failed:`, error);
      return null;
    }
  }
  
  // NEW: Call Python agent factory via subprocess
  private async callPythonAgentFactory(
    trigger: TriggerEvent,
    context: any
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      // Write trigger to temp file
      const triggerFile = `/tmp/trigger_${Date.now()}.json`;
      const contextFile = `/tmp/context_${Date.now()}.json`;
      
      Promise.all([
        writeFile(triggerFile, JSON.stringify(trigger)),
        writeFile(contextFile, JSON.stringify(context))
      ]).then(() => {
        // Call Python factory
        const pythonProcess = spawn('python3', [
          'src/agents/crewai_python/factory/generate_agent.py',
          triggerFile,
          contextFile
        ]);
        
        let stdout = '';
        let stderr = '';
        
        pythonProcess.stdout.on('data', (data) => {
          stdout += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data) => {
          stderr += data.toString();
        });
        
        pythonProcess.on('close', async (code) => {
          // Cleanup temp files
          await Promise.all([
            unlink(triggerFile).catch(() => {}),
            unlink(contextFile).catch(() => {})
          ]);
          
          if (code !== 0) {
            reject(new Error(`Python factory failed: ${stderr}`));
            return;
          }
          
          try {
            const result = JSON.parse(stdout);
            resolve(result);
          } catch (e) {
            reject(new Error(`Failed to parse factory output: ${e.message}`));
          }
        });
      }).catch(reject);
    });
  }
  
  // NEW: Execute Python agent
  private async executePythonAgent(
    agent: SpawnedAgent,
    trigger: TriggerEvent
  ): Promise<void> {
    agent.status = 'active';
    
    // Publish to Redis Stream for Python agent to consume
    const eventBus = this.eventBus as any;
    if (eventBus.publishToStream) {
      await eventBus.publishToStream('stream:agent:tasks', {
        agent_id: agent.pythonAgentId,
        trigger: trigger,
        context: agent.context
      });
    }
    
    console.log(`✅ Python agent ${agent.name} activated`);
  }
  
  private async getBusinessContext(): Promise<any> {
    // Gather current business state
    return {
      current_quarter: 'Q4',
      business_unit: 'Retail',
      constraints: ['maintain_service_level_95', 'max_markdown_20_percent'],
      budget_remaining: 250000,
      // Add more context as needed
    };
  }
  
  private getAvailableDatasets(): string[] {
    return [
      'demand_forecast',
      'inventory',
      'pricing',
      'campaign_performance',
      'sales_history',
      'customer_segments'
    ];
  }
}
```

## Step 2: Create Python Bridge Script

**File:** `src/agents/crewai_python/factory/generate_agent.py`

```python
#!/usr/bin/env python3
"""
Bridge script for generating agents from TypeScript
Called by ProactiveAgentSpawner
"""
import sys
import json
import asyncio
from agent_factory import get_agent_factory


async def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error': 'Missing arguments'}))
        sys.exit(1)
    
    trigger_file = sys.argv[1]
    context_file = sys.argv[2]
    
    # Load trigger and context
    with open(trigger_file, 'r') as f:
        trigger_event = json.load(f)
    
    with open(context_file, 'r') as f:
        context = json.load(f)
    
    # Get available datasets from context
    available_datasets = context.get('available_datasets', [])
    
    # Generate agent
    factory = get_agent_factory()
    
    try:
        agent = await factory.generate_agent_from_trigger(
            trigger_event,
            context,
            available_datasets
        )
        
        # Return agent specification
        result = {
            'success': True,
            'agent_id': f"dynamic_{agent.role.lower().replace(' ', '_')}_{int(time.time())}",
            'role': agent.role,
            'goal': agent.goal,
            'backstory': agent.backstory,
            'capabilities': getattr(agent, 'capabilities', []),
            'tools': [t.__name__ for t in agent.tools]
        }
        
        print(json.dumps(result))
        sys.exit(0)
    
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
```

Make it executable:
```bash
chmod +x src/agents/crewai_python/factory/generate_agent.py
```

## Step 3: Update Event Router

**File:** `src/services/EventRouter.mjs`

Add factory-generated agent support:

```javascript
async handleAgentActivate({ actionId, agentType, conversationId, actionText }) {
  console.log(`🤖 [Event 3: agent.activate] Activating agent: ${agentType}`);
  
  const state = this.workflowState.get(conversationId);
  if (!state) return;
  
  // Check if agent exists
  let agent = await this.agentRegistry.getAgent(agentType);
  
  if (!agent) {
    // Try auto-generation
    console.log(`   Agent ${agentType} not found. Attempting auto-generation...`);
    
    const trigger = {
      type: 'user.action.request',
      severity: 'medium',
      data: {
        action_id: actionId,
        action_text: actionText,
        conversation_id: conversationId
      }
    };
    
    agent = await this.autoGenerateAgent(trigger);
    
    if (!agent) {
      console.warn(`   Failed to auto-generate agent for ${agentType}`);
      return;
    }
  }
  
  // Execute agent...
}
```

## Step 4: Configuration

**Environment Variables:**

```bash
# .env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...
REDIS_HOST=localhost
REDIS_PORT=6379

# Agent Factory Settings
AGENT_FACTORY_ENABLED=true
AGENT_FACTORY_CACHE_ENABLED=true
AGENT_FACTORY_MODEL=gpt-4
AGENT_FACTORY_TEMPERATURE=0.2
```

## Step 5: Testing Integration

### Test 1: Trigger Auto-Generation

```typescript
// In your test file
import { ContinuousOrchestrationEngine } from './ContinuousOrchestrationEngine';

const engine = new ContinuousOrchestrationEngine(config);
await engine.start();

// Trigger event that has no matching static agent
await engine.manualTrigger(
  'custom.business.event',
  'test_source',
  {
    metric: 'revenue',
    change: -0.25,
    urgency: 'high'
  },
  'critical'
);

// Should auto-generate agent and execute
```

### Test 2: Verify Agent Registration

```sql
-- Check database for dynamically generated agents
SELECT 
  id,
  name,
  role,
  goal,
  agent_type,
  created_at
FROM agents
WHERE agent_type = 'dynamic'
ORDER BY created_at DESC
LIMIT 10;
```

### Test 3: Monitor Telemetry

```python
# In Python
from factory import get_agent_factory

factory = get_agent_factory()
telemetry = factory.get_telemetry()

print(f"Total generations: {telemetry['total_generations']}")
print(f"Cache hit rate: {telemetry['cache_hit_rate']:.2%}")
print(f"Avg generation time: {telemetry['avg_generation_time_seconds']:.2f}s")
```

## Deployment Checklist

- [ ] Install Python dependencies: `pip install -r src/agents/crewai_python/requirements.txt`
- [ ] Set environment variables (OpenAI API key, Supabase credentials)
- [ ] Test tool registry: `python src/agents/crewai_python/factory/tool_registry.py`
- [ ] Test agent factory: `python src/agents/crewai_python/factory/test_factory.py`
- [ ] Make bridge script executable: `chmod +x src/agents/crewai_python/factory/generate_agent.py`
- [ ] Update ProactiveAgentSpawner with factory integration
- [ ] Deploy to staging environment
- [ ] Monitor telemetry and error rates
- [ ] Enable in production with feature flag

## Monitoring & Observability

### Key Metrics to Track

1. **Generation Success Rate:** `successful_generations / total_attempts`
2. **Cache Hit Rate:** `cache_hits / (cache_hits + generations)`
3. **Average Generation Time:** Track P50, P95, P99
4. **Agent Execution Success Rate:** `successful_executions / total_executions`
5. **Fallback Rate:** `auto_generations / total_agent_spawns`

### Logging

```typescript
// Add structured logging
logger.info('agent_factory_called', {
  trigger_type: trigger.type,
  trigger_severity: trigger.severity,
  generation_time_ms: generationTime,
  cache_hit: cacheHit,
  agent_role: agentSpec.role
});
```

### Alerts

Set up alerts for:
- Generation failure rate > 10%
- Average generation time > 5 seconds
- Cache hit rate < 30%
- Agent execution failure rate > 20%

## Troubleshooting

### Issue: Python subprocess fails

**Check:**
- Python path is correct
- Dependencies are installed
- Bridge script has execute permissions

**Debug:**
```bash
python3 src/agents/crewai_python/factory/generate_agent.py /tmp/test_trigger.json /tmp/test_context.json
```

### Issue: Agents not registered in database

**Check:**
- Supabase credentials are set
- Database tables exist
- Network connectivity to Supabase

### Issue: Slow generation times

**Solutions:**
- Enable caching
- Use faster model (gpt-3.5-turbo)
- Pre-generate common agents
- Increase timeout limits

## Next Steps

1. **Monitor production usage** for 1-2 weeks
2. **Analyze telemetry** to identify optimization opportunities
3. **Build agent template library** for common patterns
4. **Implement few-shot learning** using successful agents as examples
5. **Add A/B testing** to compare generated vs. static agents
6. **Optimize prompt** based on real-world performance

## Support

For issues or questions:
- Check logs in `/var/log/agent-factory/`
- Review telemetry dashboard
- Contact: [your-team@example.com]
