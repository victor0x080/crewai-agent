/**
 * Verify that the server code includes problemTypeClassifier
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const serverPath = join(__dirname, '..', 'src', 'server.js');

const code = readFileSync(serverPath, 'utf8');

const checks = {
  'Has import statement': code.includes('import ProblemTypeClassifier'),
  'Has instantiation': code.includes('const problemTypeClassifier = new ProblemTypeClassifier()'),
  'Has initialization': code.includes('await problemTypeClassifier.initialize()'),
  'Has in health check': code.includes('problemTypeClassifier: problemTypeClassifier'),
  'Has in health check services object': code.match(/services:\s*\{[^}]*problemTypeClassifier/s)
};

console.log('\n🔍 Server Code Verification:\n');
Object.entries(checks).forEach(([check, passed]) => {
  console.log(`${passed ? '✅' : '❌'} ${check}: ${passed}`);
});

const allPassed = Object.values(checks).every(v => v);
console.log(`\n${allPassed ? '✅ All checks passed!' : '❌ Some checks failed!'}\n`);

process.exit(allPassed ? 0 : 1);

