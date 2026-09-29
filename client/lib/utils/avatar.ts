/**
 * Generate initials from a name or email
 * @param name - The user's display name
 * @param email - The user's email as fallback
 * @returns Two character initials
 */
export function getAvatarInitials(name?: string | null, email?: string | null): string {
  if (name) {
    // Handle names with spaces (e.g., "John Doe" -> "JD")
    const parts = name.trim().split(/\s+/)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    }
    // Single word name (e.g., "John" -> "JO")
    return name.slice(0, 2).toUpperCase()
  }
  
  if (email) {
    // Use first two characters of email before @
    const username = email.split('@')[0]
    return username.slice(0, 2).toUpperCase()
  }
  
  // Default fallback
  return 'US'
}

/**
 * Generate a background color based on a string (name or email)
 * Creates consistent colors for the same input
 * @param input - String to generate color from
 * @returns HSL color string
 */
export function getAvatarColor(input?: string | null): string {
  if (!input) {
    return 'hsl(0, 0%, 50%)' // Default gray
  }
  
  // Simple hash function to generate a number from string
  let hash = 0
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32-bit integer
  }
  
  // Generate hue from hash (0-360)
  const hue = Math.abs(hash) % 360
  
  // Use pleasant saturation and lightness values
  return `hsl(${hue}, 70%, 50%)`
}