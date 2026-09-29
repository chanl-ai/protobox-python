// Route configuration for integrations embed page

export const routeConfig = {
  // Security headers are handled by middleware
  runtime: 'edge', // Use edge runtime for better performance
  
  // Metadata for the page
  metadata: {
    title: 'ProtoBox Integrations',
    description: 'Connect your tools to enhance your workflow',
    robots: 'noindex', // Prevent indexing of embed pages
  },
  
  // Dynamic route parameters
  dynamic: 'force-dynamic', // Always render dynamically to get latest data
}