#!/usr/bin/env node

/**
 * Test script to verify MCP tokens API from frontend perspective
 */

const fetch = require('node-fetch');
const fs = require('fs');

async function testMCPTokensAPI() {
  console.log('Testing MCP tokens API from frontend perspective...\n');
  
  // Read the test token
  let token;
  try {
    token = fs.readFileSync('.test-token', 'utf8').trim();
    console.log('✓ Token loaded from .test-token');
  } catch (error) {
    console.error('✗ Failed to read .test-token:', error.message);
    console.log('  Run: make api-all to generate a token');
    process.exit(1);
  }
  
  const workspaceId = '689ce93ac66218cb8cff5637';
  const baseUrl = 'http://localhost:8090';
  
  // Test listing MCP tokens
  console.log('\n1. Testing MCP tokens list endpoint...');
  try {
    const response = await fetch(`${baseUrl}/admin/api/v1/workspaces/${workspaceId}/mcp-tokens/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      const text = await response.text();
      console.error(`✗ Failed with status ${response.status}:`, text);
    } else {
      const data = await response.json();
      console.log(`✓ Successfully retrieved ${data.length} tokens`);
      if (data.length > 0) {
        console.log('  First token:', {
          name: data[0].name,
          status: data[0].status,
          created_at: data[0].created_at
        });
      }
    }
  } catch (error) {
    console.error('✗ Request failed:', error.message);
  }
  
  // Test with missing auth header
  console.log('\n2. Testing without auth header (should fail)...');
  try {
    const response = await fetch(`${baseUrl}/admin/api/v1/workspaces/${workspaceId}/mcp-tokens/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const text = await response.text();
    if (response.status === 401 || response.status === 403) {
      console.log(`✓ Correctly rejected with ${response.status}:`, text);
    } else {
      console.error(`✗ Unexpected response ${response.status}:`, text);
    }
  } catch (error) {
    console.error('✗ Request failed:', error.message);
  }
  
  // Test with invalid token
  console.log('\n3. Testing with invalid token (should fail)...');
  try {
    const response = await fetch(`${baseUrl}/admin/api/v1/workspaces/${workspaceId}/mcp-tokens/`, {
      method: 'GET',
      headers: {
        'Authorization': 'Bearer invalid-token-12345',
        'Content-Type': 'application/json'
      }
    });
    
    const text = await response.text();
    if (response.status === 401 || response.status === 403) {
      console.log(`✓ Correctly rejected with ${response.status}:`, text);
    } else {
      console.error(`✗ Unexpected response ${response.status}:`, text);
    }
  } catch (error) {
    console.error('✗ Request failed:', error.message);
  }
  
  console.log('\n✅ Test complete');
}

// Run the test
testMCPTokensAPI().catch(console.error);