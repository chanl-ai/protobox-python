import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-8">
      <div className="max-w-4xl text-center">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">
          Mocopo Documentation
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Model Context Protocol (MCP) server with comprehensive API documentation,
          SDK guides, and integration examples for building powerful AI applications.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            href="/docs"
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            Get Started
          </Link>
          <Link
            href="/docs/api-reference"
            className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            API Reference
          </Link>
        </div>
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white rounded-lg p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              28 Admin Endpoints
            </h3>
            <p className="text-gray-600">
              Full CRUD operations for actions, secrets, and executions with interactive examples.
            </p>
          </div>
          <div className="bg-white rounded-lg p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              Python SDK
            </h3>
            <p className="text-gray-600">
              Type-safe admin client with comprehensive documentation and examples.
            </p>
          </div>
          <div className="bg-white rounded-lg p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              Action Executors
            </h3>
            <p className="text-gray-600">
              Support for REST, CODE_RUN, O3, and DATABASE action types.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}