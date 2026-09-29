/**
 * Firebase Admin Helper for E2E Testing
 * 
 * Provides utilities for managing test users with Firebase Admin SDK
 * This allows complete cleanup and user management for resilient testing.
 */

import { initializeApp, getApps, cert } from 'firebase-admin/app';
import { getAuth } from 'firebase-admin/auth';

interface TestUserCleanupData {
  email: string;
  uid?: string;
  workspaceId?: string;
}

class FirebaseAdminHelper {
  private static instance: FirebaseAdminHelper;
  private adminAuth;

  private constructor() {
    // Initialize Firebase Admin (only once)
    if (!getApps().length) {
      try {
        // In CI/testing environment, use service account
        const serviceAccount = process.env.FIREBASE_SERVICE_ACCOUNT 
          ? JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT)
          : null;

        if (serviceAccount) {
          initializeApp({
            credential: cert(serviceAccount),
            projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
          });
        } else {
          // For local testing without service account
          return;
        }
      } catch (error) {
        return;
      }
    }

    this.adminAuth = getAuth();
  }

  static getInstance(): FirebaseAdminHelper {
    if (!FirebaseAdminHelper.instance) {
      FirebaseAdminHelper.instance = new FirebaseAdminHelper();
    }
    return FirebaseAdminHelper.instance;
  }

  /**
   * Create a test user directly via Admin SDK
   */
  async createTestUser(email: string, password: string): Promise<{ uid: string }> {
    if (!this.adminAuth) {
      throw new Error('Firebase Admin not initialized');
    }

    try {
      const userRecord = await this.adminAuth.createUser({
        email,
        password,
        emailVerified: true, // Skip email verification for testing
        displayName: email.split('@')[0],
      });

      return { uid: userRecord.uid };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get custom token for test user (for programmatic login)
   */
  async getCustomToken(uid: string): Promise<string> {
    if (!this.adminAuth) {
      throw new Error('Firebase Admin not initialized');
    }

    try {
      const customToken = await this.adminAuth.createCustomToken(uid);
      return customToken;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Delete test user and cleanup
   */
  async cleanupTestUser(userData: TestUserCleanupData): Promise<void> {
    if (!this.adminAuth) {
      return;
    }

    try {
      // Delete Firebase user
      if (userData.uid) {
        await this.adminAuth.deleteUser(userData.uid);
      } else {
        // Try to find user by email
        try {
          const userRecord = await this.adminAuth.getUserByEmail(userData.email);
          await this.adminAuth.deleteUser(userRecord.uid);
        } catch (error) {
        }
      }
    } catch (error) {
    }
  }

  /**
   * Verify Firebase Admin is available
   */
  isAvailable(): boolean {
    return !!this.adminAuth;
  }

  /**
   * Get test user info
   */
  async getTestUserInfo(email: string) {
    if (!this.adminAuth) return null;

    try {
      return await this.adminAuth.getUserByEmail(email);
    } catch (error) {
      return null;
    }
  }
}

// Export singleton instance
export const firebaseAdminHelper = FirebaseAdminHelper.getInstance();

/**
 * Test user factory for generating unique test users
 */
export class TestUserFactory {
  static generateUniqueUser() {
    const timestamp = Date.now();
    const randomId = Math.random().toString(36).substring(7);
    
    return {
      email: `test-${timestamp}-${randomId}@protobox-test.com`,
      password: `TestPass123!${randomId}`,
      displayName: `Test User ${randomId}`,
      workspaceName: `Test Workspace ${timestamp}`,
    };
  }

  /**
   * Create and prepare a test user with all necessary setup
   */
  static async createFullTestUser() {
    const userData = this.generateUniqueUser();
    
    try {
      // Create Firebase user if Admin SDK is available
      if (firebaseAdminHelper.isAvailable()) {
        const { uid } = await firebaseAdminHelper.createTestUser(
          userData.email, 
          userData.password
        );
        
        return {
          ...userData,
          uid,
          customToken: await firebaseAdminHelper.getCustomToken(uid),
        };
      } else {
        // Fallback to client SDK creation (requires UI interaction)
        return userData;
      }
    } catch (error) {
      return userData; // Return basic data as fallback
    }
  }
}

/**
 * Database cleanup helper for admin API
 */
export class DatabaseCleanupHelper {
  /**
   * Clean up test data via admin API
   */
  static async cleanupTestData(baseURL: string, userData: TestUserCleanupData) {
    try {
      // This would require admin API endpoints for cleanup
      // In a real implementation:
      
      // 1. Delete user's workspaces
      if (userData.workspaceId) {
        // await adminAPI.deleteWorkspace(userData.workspaceId);
      }
      
      // 2. Delete user record from database
      // await adminAPI.deleteUser(userData.uid);
      
      // 3. Clean up any associated data (secrets, executions, etc.)
      
    } catch (error) {
    }
  }
}