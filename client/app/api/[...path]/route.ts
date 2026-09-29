import { NextRequest } from 'next/server';
import { apiProxy } from '@/lib/api/proxy';

// Sanitize path segments to prevent path traversal attacks
function sanitizePath(pathSegments: string[]): string[] {
  return pathSegments
    .filter(segment => segment && !segment.includes('..') && !segment.includes('/'))
    .map(segment => encodeURIComponent(decodeURIComponent(segment)));
}

// Generic catch-all route that proxies all API calls
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const sanitizedPath = sanitizePath(path);
  // Preserve trailing slash if the original URL had one
  const url = new URL(request.url);
  const hasTrailingSlash = url.pathname.endsWith('/');
  const endpoint = `/admin/api/v1/${sanitizedPath.join('/')}${hasTrailingSlash && !sanitizedPath[sanitizedPath.length - 1] ? '/' : ''}`;
  return apiProxy.proxyRequest(request, endpoint, { requireAuth: false });
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const sanitizedPath = sanitizePath(path);
  // Preserve trailing slash if the original URL had one
  const url = new URL(request.url);
  const hasTrailingSlash = url.pathname.endsWith('/');
  const endpoint = `/admin/api/v1/${sanitizedPath.join('/')}${hasTrailingSlash && !sanitizedPath[sanitizedPath.length - 1] ? '/' : ''}`;
  return apiProxy.proxyRequest(request, endpoint, { requireAuth: false });
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const sanitizedPath = sanitizePath(path);
  // Preserve trailing slash if the original URL had one
  const url = new URL(request.url);
  const hasTrailingSlash = url.pathname.endsWith('/');
  const endpoint = `/admin/api/v1/${sanitizedPath.join('/')}${hasTrailingSlash && !sanitizedPath[sanitizedPath.length - 1] ? '/' : ''}`;
  return apiProxy.proxyRequest(request, endpoint, { requireAuth: false });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const sanitizedPath = sanitizePath(path);
  // Preserve trailing slash if the original URL had one
  const url = new URL(request.url);
  const hasTrailingSlash = url.pathname.endsWith('/');
  const endpoint = `/admin/api/v1/${sanitizedPath.join('/')}${hasTrailingSlash && !sanitizedPath[sanitizedPath.length - 1] ? '/' : ''}`;
  return apiProxy.proxyRequest(request, endpoint, { requireAuth: false });
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const sanitizedPath = sanitizePath(path);
  // Preserve trailing slash if the original URL had one
  const url = new URL(request.url);
  const hasTrailingSlash = url.pathname.endsWith('/');
  const endpoint = `/admin/api/v1/${sanitizedPath.join('/')}${hasTrailingSlash && !sanitizedPath[sanitizedPath.length - 1] ? '/' : ''}`;
  return apiProxy.proxyRequest(request, endpoint, { requireAuth: false });
}

export async function OPTIONS() {
  const allowedOrigins = process.env.ALLOWED_ORIGINS || 'http://localhost:3000,http://localhost:3001';
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': allowedOrigins.split(',')[0],
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Allow-Credentials': 'true',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
    },
  });
}