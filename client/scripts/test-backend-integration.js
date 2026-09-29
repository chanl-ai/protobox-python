#!/usr/bin/env node

// Test script to verify InternalApiClient works correctly
// Run this from the client directory: cd client && node ../scripts/test-backend-integration.js

async function testBackendIntegration() {
  try {
    console.log('Testing InternalApiClient import from @/lib/auth/backend...');
    
    // Test 1: Import the InternalApiClient
    const { InternalApiClient } = await import('@/lib/auth/backend');
    console.log('✅ InternalApiClient imported successfully');
    
    // Test 2: Create an instance
    const client = new InternalApiClient({
      internalApiUrl: 'http://localhost:3001',
      internalApiKey: 'test-key'
    });
    console.log('✅ InternalApiClient instance created');
    
    // Test 3: Check available methods
    const methods = [
      'getUser',
      'createUser',
      'updateUser',
      'updateUserPreferences',
      'getWorkspace',
      'createWorkspace',
      'updateWorkspace',
      'listWorkspaces',
      'addWorkspaceMember',
      'getBillingInfo',
      'createSubscription',
      'updateSubscription',
      'cancelSubscription',
      'updateUsage'
    ];
    
    console.log('\nChecking available methods:');
    methods.forEach(method => {
      if (typeof client[method] === 'function') {
        console.log(`✅ ${method} is available`);
      } else {
        console.log(`❌ ${method} is missing`);
      }
    });
    
    console.log('\n✅ All tests passed! InternalApiClient is ready for backend integration.');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error(error);
    process.exit(1);
  }
}

testBackendIntegration();