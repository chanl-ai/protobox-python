import Link from 'next/link';

export default function DocsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Mocopo Documentation</h1>
      <p className="text-lg mb-8">
        Welcome to the Mocopo documentation. Mocopo is a Model Context Protocol (MCP) server 
        with comprehensive API documentation, SDK guides, and integration examples.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-3">🚀 Quick Start</h2>
          <p className="mb-4">Get up and running with Mocopo in minutes.</p>
          <Link href="/docs/quickstart" className="text-blue-600 hover:text-blue-800">
            Get Started →
          </Link>
        </div>
        
        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-3">📚 API Reference</h2>
          <p className="mb-4">Explore all 22 admin endpoints with examples.</p>
          <Link href="/docs/api-reference" className="text-blue-600 hover:text-blue-800">
            View API Docs →
          </Link>
        </div>
        
        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-3">🐍 Python SDK</h2>
          <p className="mb-4">Type-safe client with comprehensive examples.</p>
          <Link href="/docs/sdk" className="text-blue-600 hover:text-blue-800">
            SDK Documentation →
          </Link>
        </div>
        
        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-3">🔧 Integration Guides</h2>
          <p className="mb-4">Learn how to integrate with popular platforms.</p>
          <Link href="/docs/guides" className="text-blue-600 hover:text-blue-800">
            Integration Guides →
          </Link>
        </div>
      </div>
      
      <div className="mt-12">
        <h2 className="text-2xl font-bold mb-4">Features</h2>
        <ul className="list-disc list-inside space-y-2">
          <li><strong>28 Admin Endpoints</strong> - Complete CRUD operations for actions, secrets, and executions</li>
          <li><strong>4 Action Types</strong> - REST, CODE_RUN, O3, and DATABASE executors</li>
          <li><strong>Secure Code Execution</strong> - Sandboxed Python execution with Docker</li>
          <li><strong>Secret Management</strong> - AES-256-GCM encryption</li>
          <li><strong>MongoDB Integration</strong> - Async operations with connection pooling</li>
        </ul>
      </div>
    </div>
  );
}