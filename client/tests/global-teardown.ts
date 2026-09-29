import type { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  
  // Any cleanup needed after all tests complete
  
}

export default globalTeardown;