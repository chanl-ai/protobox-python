export interface ValidationResult {
  isValid: boolean
  error?: string
}

export interface ValidationRules {
  required?: boolean
  minLength?: number
  maxLength?: number
  pattern?: RegExp
  custom?: (value: any) => boolean | string
}

// Email validation regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Password validation rules
export const PASSWORD_MIN_LENGTH = 6

export function validateEmail(email: string): ValidationResult {
  if (!email || email.trim() === '') {
    return { isValid: false, error: 'Email is required' }
  }
  
  if (!EMAIL_REGEX.test(email)) {
    return { isValid: false, error: 'Please enter a valid email address' }
  }
  
  return { isValid: true }
}

export function validatePassword(password: string): ValidationResult {
  if (!password || password.trim() === '') {
    return { isValid: false, error: 'Password is required' }
  }
  
  if (password.length < PASSWORD_MIN_LENGTH) {
    return { isValid: false, error: `Password must be at least ${PASSWORD_MIN_LENGTH} characters` }
  }
  
  return { isValid: true }
}

export function validatePasswordStrength(password: string): {
  isStrong: boolean
  strength: 'weak' | 'medium' | 'strong'
  suggestions: string[]
} {
  const suggestions: string[] = []
  let strength: 'weak' | 'medium' | 'strong' = 'weak'
  
  // Check length
  if (password.length < 8) {
    suggestions.push('Use at least 8 characters')
  }
  
  // Check for uppercase
  if (!/[A-Z]/.test(password)) {
    suggestions.push('Include at least one uppercase letter')
  }
  
  // Check for lowercase
  if (!/[a-z]/.test(password)) {
    suggestions.push('Include at least one lowercase letter')
  }
  
  // Check for numbers
  if (!/\d/.test(password)) {
    suggestions.push('Include at least one number')
  }
  
  // Check for special characters
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    suggestions.push('Include at least one special character')
  }
  
  // Determine strength
  const criteriasMet = 5 - suggestions.length
  if (criteriasMet >= 4) {
    strength = 'strong'
  } else if (criteriasMet >= 3) {
    strength = 'medium'
  }
  
  return {
    isStrong: strength === 'strong',
    strength,
    suggestions
  }
}

export function validateField(value: any, rules: ValidationRules): ValidationResult {
  // Required check
  if (rules.required && (!value || value.toString().trim() === '')) {
    return { isValid: false, error: 'This field is required' }
  }
  
  // Skip other validations if not required and empty
  if (!value || value.toString().trim() === '') {
    return { isValid: true }
  }
  
  const stringValue = value.toString()
  
  // Min length check
  if (rules.minLength && stringValue.length < rules.minLength) {
    return { 
      isValid: false, 
      error: `Must be at least ${rules.minLength} characters` 
    }
  }
  
  // Max length check
  if (rules.maxLength && stringValue.length > rules.maxLength) {
    return { 
      isValid: false, 
      error: `Must be no more than ${rules.maxLength} characters` 
    }
  }
  
  // Pattern check
  if (rules.pattern && !rules.pattern.test(stringValue)) {
    return { isValid: false, error: 'Invalid format' }
  }
  
  // Custom validation
  if (rules.custom) {
    const customResult = rules.custom(value)
    if (typeof customResult === 'string') {
      return { isValid: false, error: customResult }
    }
    if (!customResult) {
      return { isValid: false, error: 'Validation failed' }
    }
  }
  
  return { isValid: true }
}

export function validateForm(
  data: Record<string, any>,
  rules: Record<string, ValidationRules>
): { isValid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {}
  
  for (const [field, fieldRules] of Object.entries(rules)) {
    const result = validateField(data[field], fieldRules)
    if (!result.isValid && result.error) {
      errors[field] = result.error
    }
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  }
}