#!/bin/bash
#
# Stop Production Services
#

echo "Stopping production services..."

# Stop Python agents
echo "Stopping Python agents..."
pkill -f "start_all_agents.py" 2>/dev/null && echo "✅ Python agents stopped" || echo "⚠️  No Python agents running"

# Stop Node.js backend
echo "Stopping Node.js backend..."
pkill -f "node.*server.js" 2>/dev/null && echo "✅ Backend stopped" || echo "⚠️  No backend running"
pkill -f "npm.*start" 2>/dev/null && echo "✅ Backend stopped" || echo "⚠️  No backend running"

# Optionally stop Redis (uncomment if needed)
# echo "Stopping Redis..."
# redis-cli shutdown 2>/dev/null && echo "✅ Redis stopped" || echo "⚠️  Redis not running"

echo ""
echo "All services stopped!"

