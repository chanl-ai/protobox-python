#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function getBuildInfo() {
  let gitCommit = 'unknown';
  let gitBranch = 'unknown';
  let buildTime = new Date().toISOString();
  
  try {
    // Try to get git info from current directory first
    gitCommit = execSync('git rev-parse --short HEAD').toString().trim();
    gitBranch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
  } catch (error) {
    // If we're in Vercel, try from parent directory
    if (process.env.VERCEL === '1') {
      try {
        gitCommit = execSync('git rev-parse --short HEAD', { cwd: '..' }).toString().trim();
        gitBranch = execSync('git rev-parse --abbrev-ref HEAD', { cwd: '..' }).toString().trim();
      } catch (parentError) {
        console.warn('Could not get git info from parent directory:', parentError.message);
      }
    } else {
      console.warn('Could not get git info:', error.message);
    }
  }
  
  return {
    gitCommit,
    gitBranch,
    buildTime,
    version: process.env.npm_package_version || '0.0.0'
  };
}

const buildInfo = getBuildInfo();
const outputPath = path.join(__dirname, '..', 'lib', 'build-info.ts');

const content = `// Auto-generated build info - DO NOT EDIT
// Generated at: ${buildInfo.buildTime}

export const BUILD_INFO = {
  gitCommit: '${buildInfo.gitCommit}',
  gitBranch: '${buildInfo.gitBranch}',
  buildTime: '${buildInfo.buildTime}',
  version: '${buildInfo.version}'
} as const;
`;

// Ensure directory exists
const dir = path.dirname(outputPath);
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

fs.writeFileSync(outputPath, content);
console.log(`✅ Build info generated: ${outputPath}`);
console.log(`   Git commit: ${buildInfo.gitCommit}`);
console.log(`   Git branch: ${buildInfo.gitBranch}`);