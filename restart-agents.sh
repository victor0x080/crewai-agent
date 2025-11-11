#!/bin/bash
# Restart all agents with fixes applied

echo "🛑 Stopping all agents..."
pkill -f "start_all_agents.py" 2>/dev/null || true
pkill -f "runners/.*\.py" 2>/dev/null || true
sleep 2

echo "🚀 Starting all agents..."
cd /home/KJB
source venv/bin/activate
export API_URL=http://localhost:3001

# Start agents in background
python agents/start_all_agents.py > logs/python-agents.log 2> logs/python-agents-error.log &

echo "⏳ Waiting for agents to initialize..."
sleep 10

echo "📊 Checking active agents..."
ACTIVE_COUNT=$(redis-cli KEYS "crewai:agent:*:heartbeat" 2>/dev/null | wc -l)
echo "✅ Active agents: $ACTIVE_COUNT"

echo ""
echo "📋 Active agent list:"
redis-cli KEYS "crewai:agent:*:heartbeat" 2>/dev/null | sed 's/crewai:agent://g' | sed 's/:heartbeat//g' | sort

echo ""
echo "📝 Check logs:"
echo "   tail -f logs/python-agents.log"
echo "   tail -f logs/python-agents-error.log"

