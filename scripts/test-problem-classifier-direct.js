/**
 * Direct test of ProblemTypeClassifier service
 */

import ProblemTypeClassifier from '../src/services/ProblemTypeClassifier.js';

async function testClassifier() {
  console.log('Testing ProblemTypeClassifier...\n');
  
  const classifier = new ProblemTypeClassifier();
  await classifier.initialize();
  
  console.log('Classifier healthy:', classifier.isHealthy());
  console.log('');
  
  const testQueries = [
    'alert me if there is a risk',
    'help me understand the situation',
    'solve this problem',
    'monitor this situation',
    'automate this process'
  ];
  
  for (const query of testQueries) {
    console.log(`Query: "${query}"`);
    try {
      const result = await classifier.classifyProblemType(query, {});
      console.log(`  Problem Type: ${result.problemType}`);
      console.log(`  Workflow Stage: ${result.workflowStage}`);
      console.log(`  Confidence: ${result.confidence}`);
      console.log(`  Problem Space: ${result.problemSpace}`);
      console.log('');
    } catch (error) {
      console.error(`  Error: ${error.message}`);
      console.log('');
    }
  }
  
  process.exit(0);
}

testClassifier().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});

