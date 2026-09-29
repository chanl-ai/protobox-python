import { NextRequest, NextResponse } from 'next/server';

interface ProxyConfig {
  baseUrl: string;
  timeout?: number;
  retries?: number;
}

interface ProxyOptions {
  method?: string;
  requireAuth?: boolean;
  transformRequest?: (body: any) => any;
  transformResponse?: (data: any) => any;
}

export class ApiProxy {
  private config: ProxyConfig;

  constructor(config: ProxyConfig) {
    this.config = {
      timeout: 10000,
      retries: 3,
      ...config
    };
  }

  async proxyRequest(
    request: NextRequest,
    endpoint: string,
    options: ProxyOptions = {}
  ): Promise<NextResponse> {
    const {
      method = request.method,
      requireAuth = true,
      transformRequest,
      transformResponse
    } = options;

    try {
      // Check if we're in local development mode (no auth)
      const isLocalDev = process.env.NODE_ENV === 'development' && 
                        !process.env.NEXT_PUBLIC_API_URL?.startsWith('https://');

      // Auth validation - check cookie first, then header
      let authToken: string | null = null;
      
      if (requireAuth && !isLocalDev) {
        // First try to get token from cookie
        const cookieHeader = request.headers.get('cookie');
        if (cookieHeader) {
          const cookies = cookieHeader.split(';').map(c => c.trim());
          const authCookie = cookies.find(c => c.startsWith('auth-token='));
          if (authCookie) {
            authToken = authCookie.split('=')[1];
          }
        }
        
        // Fallback to authorization header
        if (!authToken) {
          const authHeader = request.headers.get('authorization');
          if (authHeader?.startsWith('Bearer ')) {
            authToken = authHeader.substring(7);
          }
        }
        
        if (!authToken) {
          return this.errorResponse('Unauthorized', 401);
        }
      } else if (!requireAuth || isLocalDev) {
        // Still try to get token if available, but don't require it
        const cookieHeader = request.headers.get('cookie');
        if (cookieHeader) {
          const cookies = cookieHeader.split(';').map(c => c.trim());
          const authCookie = cookies.find(c => c.startsWith('auth-token='));
          if (authCookie) {
            authToken = authCookie.split('=')[1];
          }
        }
      }

      // Extract request body if needed
      let body: any = null;
      if (['POST', 'PUT', 'PATCH'].includes(method)) {
        body = await request.json().catch(() => null);
        if (transformRequest && body) {
          body = transformRequest(body);
        }
      }

      // Build headers
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (isLocalDev && !authToken) {
        // In local dev with no auth, add test user header
        headers['X-User-ID'] = 'dev_user';
      } else if (authToken) {
        // Forward auth token (from cookie or header)
        headers['Authorization'] = `Bearer ${authToken}`;
      } else {
        // If no authToken was found but there's an auth header, forward it
        const authHeader = request.headers.get('authorization');
        if (authHeader) {
          headers['Authorization'] = authHeader;
        }
      }

      // Forward other relevant headers
      const userAgent = request.headers.get('user-agent');
      if (userAgent) {
        headers['User-Agent'] = userAgent;
      }

      // Make request to backend
      const url = `${this.config.baseUrl}${endpoint}`;

      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: AbortSignal.timeout(this.config.timeout!),
      });

      // Handle response
      let data: any;
      const contentType = response.headers.get('content-type');
      
      if (contentType?.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      // Transform response if needed
      if (transformResponse && response.ok) {
        data = transformResponse(data);
      }

      // Return response with same status
      return NextResponse.json(data, { 
        status: response.status,
        headers: this.getCorsHeaders()
      });

    } catch (error) {
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return this.errorResponse('Request timeout', 408);
        }
        return this.errorResponse('Internal server error', 500);
      }
      
      return this.errorResponse('Unknown error', 500);
    }
  }

  private errorResponse(message: string, status: number): NextResponse {
    return NextResponse.json(
      { 
        error: message,
        status,
        timestamp: new Date().toISOString()
      },
      { 
        status,
        headers: this.getCorsHeaders()
      }
    );
  }

  private getCorsHeaders(): Record<string, string> {
    const allowedOrigins = process.env.ALLOWED_ORIGINS || 'http://localhost:3000,http://localhost:3001';
    return {
      'Access-Control-Allow-Origin': allowedOrigins.split(',')[0], // Use first allowed origin
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Allow-Credentials': 'true',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
    };
  }
}

// Create singleton instance
export const apiProxy = new ApiProxy({
  baseUrl: process.env.MCP_SERVER_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8090',
  timeout: 15000,
  retries: 3
});