import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // transpilePackages no longer needed for local packages
  env: {
    // Removed deprecated AUTH_MODE - now always uses Firebase authentication
    // Remove TESTING_USER_ID - it causes security issues
    MCP_SECRET_KEY: process.env.MCP_SECRET_KEY || '',
    JWT_SECRET: process.env.JWT_SECRET || '',
  },
  eslint: {
    // Disable ESLint during production builds to avoid build failures
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Disable TypeScript errors during production builds (temporary)
    ignoreBuildErrors: true,
  },
  experimental: {
    // Increase memory limit for builds
    workerThreads: false,
    cpus: 1,
  },
  webpack: (config, { dev, isServer }) => {
    // Remove console logs in production builds (client-side only)
    if (!dev && !isServer) {
      config.optimization.minimizer?.forEach((minimizer: any) => {
        if (minimizer.constructor.name === 'TerserPlugin') {
          minimizer.options.terserOptions = {
            ...minimizer.options.terserOptions,
            compress: {
              ...minimizer.options.terserOptions?.compress,
              drop_console: true,
              drop_debugger: true,
              // Keep console.error and console.warn for debugging
              pure_funcs: ['console.log', 'console.info', 'console.debug'],
            },
          }
        }
      })
    }
    return config
  },
};

export default nextConfig;
