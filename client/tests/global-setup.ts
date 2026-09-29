import type { FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  
  // Ensure .auth directory exists
  const fs = require('fs');
  const path = require('path');
  
  const authDir = path.join(__dirname, '../.auth');
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }
  
}

export default globalSetup;