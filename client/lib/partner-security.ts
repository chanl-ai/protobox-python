// Partner security configuration and domain validation

export interface PartnerDomain {
  id: string
  partnerId: string
  domain: string
  isActive: boolean
  createdAt: Date
  verifiedAt?: Date
  verificationToken?: string
}

export interface PartnerSecurityConfig {
  partnerId: string
  allowedDomains: string[]
  requireHttps: boolean
  allowLocalhost: boolean
  allowSubdomains: boolean
  maxDomains: number
}

// Default security settings
export const DEFAULT_PARTNER_SECURITY: Partial<PartnerSecurityConfig> = {
  requireHttps: true,
  allowLocalhost: false,
  allowSubdomains: false,
  maxDomains: 10
}

export class PartnerSecurityValidator {
  private config: PartnerSecurityConfig

  constructor(config: PartnerSecurityConfig) {
    this.config = {
      ...DEFAULT_PARTNER_SECURITY,
      ...config
    }
  }

  /**
   * Validate if a domain is allowed for this partner
   */
  validateDomain(domain: string): { valid: boolean; reason?: string } {
    // Check if domain is in allowed list
    const isAllowed = this.config.allowedDomains.some(allowed => {
      if (this.config.allowSubdomains && allowed.startsWith('*.')) {
        const baseDomain = allowed.substring(2)
        return domain === baseDomain || domain.endsWith(`.${baseDomain}`)
      }
      return domain === allowed
    })

    if (!isAllowed) {
      return { valid: false, reason: 'Domain not in whitelist' }
    }

    // Check HTTPS requirement
    if (this.config.requireHttps && !this.config.allowLocalhost) {
      const isLocalhost = ['localhost', '127.0.0.1', '0.0.0.0'].includes(domain.split(':')[0])
      if (!isLocalhost) {
        // In real implementation, we'd check the protocol from the request
        // For now, we'll assume HTTPS is required for non-localhost
      }
    }

    return { valid: true }
  }

  /**
   * Validate if an origin (protocol + domain + port) is allowed
   */
  validateOrigin(origin: string): { valid: boolean; reason?: string } {
    try {
      const url = new URL(origin)
      
      // Check protocol
      if (this.config.requireHttps && url.protocol !== 'https:') {
        const isLocalhost = ['localhost', '127.0.0.1', '0.0.0.0'].includes(url.hostname)
        if (!isLocalhost || !this.config.allowLocalhost) {
          return { valid: false, reason: 'HTTPS required' }
        }
      }

      // Validate domain
      return this.validateDomain(url.hostname)
    } catch (error) {
      return { valid: false, reason: 'Invalid origin URL' }
    }
  }

  /**
   * Add a new domain to the whitelist
   */
  addDomain(domain: string): { success: boolean; reason?: string } {
    // Check max domains limit
    if (this.config.allowedDomains.length >= this.config.maxDomains) {
      return { success: false, reason: `Maximum ${this.config.maxDomains} domains allowed` }
    }

    // Validate domain format
    if (!this.isValidDomainFormat(domain)) {
      return { success: false, reason: 'Invalid domain format' }
    }

    // Check if already exists
    if (this.config.allowedDomains.includes(domain)) {
      return { success: false, reason: 'Domain already exists' }
    }

    this.config.allowedDomains.push(domain)
    return { success: true }
  }

  /**
   * Remove a domain from the whitelist
   */
  removeDomain(domain: string): boolean {
    const index = this.config.allowedDomains.indexOf(domain)
    if (index > -1) {
      this.config.allowedDomains.splice(index, 1)
      return true
    }
    return false
  }

  /**
   * Generate a verification token for domain ownership verification
   */
  static generateVerificationToken(): string {
    return `protobox-verify-${crypto.randomUUID()}`
  }

  /**
   * Generate verification instructions for a domain
   */
  static getVerificationInstructions(domain: string, token: string): {
    method: string
    instructions: string
    verificationUrl: string
  } {
    return {
      method: 'TXT Record',
      instructions: `Add a TXT record to your domain's DNS with the following value: ${token}`,
      verificationUrl: `https://localhost:8090/v1/partners/verify-domain?domain=${domain}&token=${token}`
    }
  }

  private isValidDomainFormat(domain: string): boolean {
    // Basic domain validation
    const domainRegex = /^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z]{2,}$/
    return domainRegex.test(domain)
  }
}

// Mock function to simulate fetching partner domains from database
export async function getPartnerDomains(partnerId: string): Promise<string[]> {
  // In production, this would fetch from database
  // For now, return mock data based on partner ID
  const mockDomains: Record<string, string[]> = {
    'test_partner_dev': [
      'localhost:3000',
      'localhost:3001',
      '*.test-partner.com'
    ],
    'demo_partner': [
      'demo.example.com',
      '*.demo.example.com'
    ]
  }

  return mockDomains[partnerId] || []
}

// Mock function to simulate validating partner access
export async function validatePartnerAccess(
  partnerId: string, 
  origin: string
): Promise<{ valid: boolean; reason?: string }> {
  // Get partner domains
  const allowedDomains = await getPartnerDomains(partnerId)
  
  // Create validator
  const validator = new PartnerSecurityValidator({
    partnerId,
    allowedDomains,
    requireHttps: process.env.NODE_ENV === 'production',
    allowLocalhost: process.env.NODE_ENV === 'development',
    allowSubdomains: true,
    maxDomains: 10
  })

  return validator.validateOrigin(origin)
}