/**
 * Configuration Management
 * Loads and validates environment variables
 */

import dotenv from 'dotenv';

dotenv.config();

const config = {
  // Server
  port: parseInt(process.env.PORT || '3002', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
  
  // OpenAI
  openai: {
    enabled: !!process.env.OPENAI_API_KEY,
    apiKey: process.env.OPENAI_API_KEY,
    model: process.env.OPENAI_MODEL || 'gpt-4-turbo-preview',
    temperature: parseFloat(process.env.OPENAI_TEMPERATURE || '0.7'),
    maxTokens: parseInt(process.env.OPENAI_MAX_TOKENS || '2000', 10)
  },
  
  // Supabase
  supabase: {
    enabled: !!process.env.SUPABASE_URL && !!process.env.SUPABASE_ANON_KEY,
    url: process.env.SUPABASE_URL,
    anonKey: process.env.SUPABASE_ANON_KEY,
    serviceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY
  },
  
  // Redis (ENABLED BY DEFAULT for production - use real agents)
  redis: {
    enabled: process.env.ENABLE_REDIS !== 'false', // Default TRUE (only disable explicitly)
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379', 10),
    password: process.env.REDIS_PASSWORD || undefined,
    retryStrategy: (times) => {
      const delay = Math.min(times * 50, 2000);
      return delay;
    }
  },
  
  // Agent Configuration
  maxAgentTimeoutMs: parseInt(process.env.MAX_AGENT_TIMEOUT_MS || '300000', 10), // 300 seconds (5 minutes)
  enableBackgroundProcessing: process.env.ENABLE_BACKGROUND_PROCESSING !== 'false',
  
  // Task Backlog Configuration
  backlog: {
    enabled: process.env.ENABLE_TASK_BACKLOG !== 'false', // Default TRUE
    maxConcurrent: parseInt(process.env.MAX_CONCURRENT_TASKS || '10', 10),
    taskTimeout: parseInt(process.env.TASK_TIMEOUT_MS || '300000', 10), // 5 minutes
    enableMetrics: process.env.ENABLE_BACKLOG_METRICS !== 'false'
  },
  
  // Pinecone
  pinecone: {
    enabled: !!process.env.PINECONE_API_KEY,
    apiKey: process.env.PINECONE_API_KEY,
    indexName: process.env.PINECONE_INDEX_NAME || 'langchain-chatbot-memory',
    namespace: process.env.PINECONE_NAMESPACE || 'default',
    dimension: parseInt(process.env.PINECONE_DIMENSION || '1024', 10), // Default to 1024, can be 1536 for OpenAI
    environment: process.env.PINECONE_ENVIRONMENT || null, // Extract from host URL if provided
    host: process.env.PINECONE_HOST || null, // Optional host URL
    embeddingModel: process.env.PINECONE_EMBEDDING_MODEL || 'text-embedding-3-large' // Embedding model to use
  },
  
  // Logging
  logLevel: process.env.LOG_LEVEL || 'info'
};

// Validate required configuration
function validate() {
  const errors = [];
  
  if (!config.openai.enabled) {
    errors.push('OPENAI_API_KEY is required');
  }
  
  if (!config.supabase.enabled) {
    errors.push('SUPABASE_URL and SUPABASE_ANON_KEY are required');
  }
  
  if (errors.length > 0) {
    throw new Error(`Configuration validation failed:\n  - ${errors.join('\n  - ')}`);
  }
}

validate();

export default config;


