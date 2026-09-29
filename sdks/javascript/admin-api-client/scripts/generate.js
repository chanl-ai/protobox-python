#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ADMIN_API_URL = process.env.ADMIN_API_URL || 'http://localhost:8090';
const OUTPUT_DIR = path.join(__dirname, '..', 'src', 'generated');

console.log('🚀 Generating ProtoBox Admin API TypeScript Client');
console.log(`📍 Admin API URL: ${ADMIN_API_URL}`);
console.log(`📂 Output directory: ${OUTPUT_DIR}`);

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

try {
  // Fetch OpenAPI spec
  console.log('\n📥 Fetching OpenAPI specification...');
  const openApiUrl = `${ADMIN_API_URL}/openapi.json`;

  execSync(`curl -s "${openApiUrl}" -o openapi.json`, { stdio: 'inherit' });

  // Verify spec was downloaded
  if (!fs.existsSync('openapi.json')) {
    throw new Error('Failed to download OpenAPI spec');
  }

  // Generate TypeScript client
  console.log('\n⚙️  Generating TypeScript client...');
  execSync(`npx @hey-api/openapi-ts -i openapi.json -o ${OUTPUT_DIR}`, {
    stdio: 'inherit',
  });

  // Clean up
  fs.unlinkSync('openapi.json');

  console.log('\n✅ Client generated successfully!');
  console.log(`📁 Generated files: ${OUTPUT_DIR}`);
} catch (error) {
  console.error('\n❌ Error generating client:', error.message);
  process.exit(1);
}
