/**
 * Backend integration for auth - simplified to use direct API calls
 */

import { protoboxClient } from '@/lib/api/protobox-client'

export const backendIntegration = {
  /**
   * Exchange Firebase token for backend JWT
   */
  exchangeToken: async (firebaseToken: string) => {
    try {
      const response = await protoboxClient.exchangeToken(firebaseToken)
      return {
        success: true,
        token: response.data?.access_token,
        refreshToken: response.data?.refresh_token,
        user: response.data?.user
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Token exchange failed'
      }
    }
  },

  /**
   * Refresh JWT token
   */
  refreshToken: async () => {
    try {
      const response = await protoboxClient.refreshToken()
      return {
        success: true,
        token: response.data?.access_token,
        refreshToken: response.data?.refresh_token
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Token refresh failed'
      }
    }
  },

  /**
   * Validate current token
   */
  validateToken: async () => {
    try {
      const response = await protoboxClient.validateToken()
      return {
        success: true,
        valid: response.data?.valid,
        user: response
      }
    } catch (error) {
      return {
        success: false,
        valid: false
      }
    }
  }
}