/**
 * Structured Logger
 * Outputs JSON logs for easy parsing and monitoring
 */

import config from '../config/index.js';

const LOG_LEVELS = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3
};

const currentLevel = LOG_LEVELS[config.logLevel] || LOG_LEVELS.info;

function log(level, message, data = {}) {
  if (LOG_LEVELS[level] < currentLevel) {
    return;
  }
  
  const logEntry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...data
  };
  
  const output = JSON.stringify(logEntry);
  
  if (level === 'error') {
    console.error(output);
  } else {
    console.log(output);
  }
}

export const logger = {
  debug: (message, data) => log('debug', message, data),
  info: (message, data) => log('info', message, data),
  warn: (message, data) => log('warn', message, data),
  error: (message, data) => log('error', data)
};


