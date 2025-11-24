#!/bin/bash

# Test script for CrewAI Conversational Agent via /api/process-message endpoint

BASE_URL="http://localhost:3001"
ENDPOINT="${BASE_URL}/api/process-message"

echo "🧪 Testing CrewAI Conversational Agent"
echo "======================================"
echo ""

# Test 1: First message with conversationId (triggers CrewAI agent)
echo "📨 Test 1: First message with conversationId"
echo "--------------------------------------------"
curl -X POST "${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, my name is Alice. What can you help me with?",
    "conversationId": "test_conv_001",
    "context": {
      "userId": "test_user_123",
      "tenantId": "test_tenant"
    }
  }' | jq '.'

echo ""
echo ""

# Wait a bit
sleep 2

# Test 2: Follow-up message (should remember name)
echo "📨 Test 2: Follow-up message (should remember name)"
echo "---------------------------------------------------"
curl -X POST "${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my name?",
    "conversationId": "test_conv_001",
    "context": {
      "userId": "test_user_123",
      "tenantId": "test_tenant"
    }
  }' | jq '.'

echo ""
echo ""

# Test 3: Message without conversationId (uses LangChain chatbot)
echo "📨 Test 3: Message without conversationId (LangChain fallback)"
echo "----------------------------------------------------------------"
curl -X POST "${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is 2+2?",
    "context": {
      "userId": "test_user_123",
      "tenantId": "test_tenant"
    }
  }' | jq '.'

echo ""
echo "✅ Tests completed!"

