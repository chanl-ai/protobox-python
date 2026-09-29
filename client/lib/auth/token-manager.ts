/**
 * Centralized token management - single source of truth for JWT tokens
 */

class TokenManager {
  private jwtToken: string | null = null;
  private listeners: ((token: string | null) => void)[] = [];

  /**
   * Initialize token from cookie on startup
   */
  initialize() {
    if (typeof window !== 'undefined') {
      const token = this.getTokenFromCookie();
      if (token) {
        this.jwtToken = token;
      }
    }
  }

  /**
   * Set JWT token and notify all listeners
   */
  setToken(token: string | null) {
    this.jwtToken = token;
    
    // Update cookie
    if (typeof window !== 'undefined') {
      if (token) {
        document.cookie = `auth-token=${token}; path=/; max-age=604800; SameSite=Lax`;
      } else {
        document.cookie = 'auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
      }
    }
    
    // Notify all listeners
    this.listeners.forEach(listener => listener(token));
  }

  /**
   * Get current JWT token
   */
  getToken(): string | null {
    return this.jwtToken;
  }

  /**
   * Get authorization header for API requests
   */
  getAuthHeader(): Record<string, string> {
    return this.jwtToken ? { 'Authorization': `Bearer ${this.jwtToken}` } : {};
  }

  /**
   * Subscribe to token changes
   */
  subscribe(listener: (token: string | null) => void): () => void {
    this.listeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  /**
   * Check if current token is expired or about to expire
   * @param bufferMinutes - Minutes before expiry to consider token as expired (default: 5)
   * @returns true if token is expired or will expire soon
   */
  isTokenExpired(bufferMinutes: number = 5): boolean {
    if (!this.jwtToken) return true;
    
    try {
      // JWT tokens have 3 parts: header.payload.signature
      const parts = this.jwtToken.split('.');
      if (parts.length !== 3) return true;
      
      // Decode payload (base64url)
      const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
      
      // Check expiration time
      if (!payload.exp) return false; // No expiration means token doesn't expire
      
      const now = Math.floor(Date.now() / 1000); // Current time in seconds
      const bufferSeconds = bufferMinutes * 60;
      
      return payload.exp <= (now + bufferSeconds);
    } catch (error) {
      // If we can't parse the token, consider it expired
      return true;
    }
  }

  /**
   * Clear token and notify listeners
   */
  clearToken() {
    this.setToken(null);
  }

  /**
   * Get token from cookie (fallback for SSR)
   */
  private getTokenFromCookie(): string | null {
    if (typeof window === 'undefined') return null;
    
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === 'auth-token') {
        return value || null;
      }
    }
    return null;
  }
}

// Export singleton instance
export const tokenManager = new TokenManager();

// Initialize on import
tokenManager.initialize();