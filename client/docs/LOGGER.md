# Enhanced Production Logger

A sophisticated logging utility that provides production debugging capabilities while keeping console clean by default.

## Features

- 🔇 **Silent in Production** - No logs by default in production builds
- 🐛 **Production Debugging** - Enable logging in production for troubleshooting
- 🏷️ **Namespace Support** - Filter logs by component/feature
- 📊 **Log Levels** - Control verbosity with debug/log/info/warn/error levels
- 💾 **Persistent Settings** - Settings saved in localStorage
- 🔗 **URL Control** - Enable debugging via URL parameters
- 🌍 **Global Access** - Available globally for emergency debugging

## Basic Usage

```typescript
import logger from '@/lib/utils/console';

// Basic logging (works in development, silent in production)
logger.log('User signed in', { userId: '123' });
logger.info('API response received');
logger.warn('Deprecated method used');
logger.error('Authentication failed');

// Namespaced logging
const apiLogger = logger.namespace('api');
apiLogger.log('GET /users response:', data);

const authLogger = logger.namespace('auth');
authLogger.debug('Token validation started');
```

## Production Debugging

### Method 1: Browser Console (Emergency Access)
```javascript
// In production browser console:
__logger.enableDebug();
__logger.log('Debug message now visible!');
```

### Method 2: URL Parameters
```
http://localhost:3010?debug=true&debug-namespaces=api,auth
```

### Method 3: localStorage
```javascript
// Persist debug settings across sessions
localStorage.setItem('debug', 'true');
localStorage.setItem('debug-namespaces', 'api,auth');
localStorage.setItem('debug-level', 'debug');
// Refresh page to apply
```

### Method 4: Programmatic Control
```typescript
import logger from '@/lib/utils/console';

// Enable debugging
logger.enableDebug();

// Enable specific namespaces
logger.enableNamespace('api', 'auth', 'billing');

// Set minimum log level
logger.setLevel('debug');

// Clear all debug settings
logger.clearDebugSettings();
```

## Advanced Usage

### Namespaced Loggers
```typescript
// Create dedicated loggers for different components
const apiLogger = logger.namespace('api');
const authLogger = logger.namespace('auth');
const billingLogger = logger.namespace('billing');

// Use them throughout your code
apiLogger.info('API call started', { endpoint: '/users' });
authLogger.warn('Token expires soon');
billingLogger.error('Payment failed', { error });
```

### Conditional Debugging by Namespace
```typescript
// Only show API logs in production
logger.enableNamespace('api');

// Show all logs with wildcard
logger.enableNamespace('*');

// Check status
logger.getStatus();
// Returns: { isDevelopment: false, debugEnabled: true, enabledNamespaces: ['api'], logLevel: 'log' }
```

### Structured Logging
```typescript
const userLogger = logger.namespace('user');

userLogger.group('User Registration Process');
userLogger.log('Validating email:', email);
userLogger.log('Creating user record');
userLogger.table({ email, userId, plan });
userLogger.groupEnd();
```

## Production Troubleshooting Guide

### Quick Debug Enable
1. Open browser dev tools console
2. Run: `__logger.enableDebug()`
3. Refresh page or trigger the issue
4. Logs will now appear with 🐛 prefix

### Namespace Filtering
```javascript
// Only show API-related logs
__logger.enableNamespace('api');

// Show multiple namespaces
__logger.enableNamespace('api', 'auth', 'billing');

// Show everything
__logger.enableNamespace('*');
```

### Log Level Control
```javascript
// Only show warnings and errors
__logger.setLevel('warn');

// Show everything including debug
__logger.setLevel('debug');
```

### Session Information
```javascript
// Get debug session info
__logger.getStatus();
// Returns session ID, enabled namespaces, etc.
```

## Migration from console.*

### Before
```typescript
console.log('User data:', userData);
console.error('Failed to save:', error);
console.warn('Deprecated API usage');
```

### After
```typescript
import logger from '@/lib/utils/console';

logger.log('User data:', userData);
logger.error('Failed to save:', error);
logger.warn('Deprecated API usage');

// Or with namespace
const userLogger = logger.namespace('user');
userLogger.log('User data:', userData);
```

## Integration Examples

### API Client
```typescript
import logger from '@/lib/utils/console';

const apiLogger = logger.namespace('api');

export class ApiClient {
  async request(endpoint: string) {
    apiLogger.log('Starting request:', endpoint);
    
    try {
      const response = await fetch(endpoint);
      apiLogger.info('Response received:', response.status);
      return response.json();
    } catch (error) {
      apiLogger.error('Request failed:', error);
      throw error;
    }
  }
}
```

### Authentication
```typescript
import logger from '@/lib/utils/console';

const authLogger = logger.namespace('auth');

export const authService = {
  async login(email: string) {
    authLogger.log('Login attempt for:', email);
    
    try {
      const token = await this.authenticate(email);
      authLogger.info('Login successful');
      return token;
    } catch (error) {
      authLogger.error('Login failed:', error);
      throw error;
    }
  }
};
```

### Billing
```typescript
import logger from '@/lib/utils/console';

const billingLogger = logger.namespace('billing');

export const billingService = {
  async processPayment(amount: number) {
    billingLogger.log('Processing payment:', { amount });
    
    // Payment logic
    billingLogger.info('Payment processed successfully');
  }
};
```

## Best Practices

1. **Use Namespaces** - Always use namespaced loggers for better filtering
2. **Appropriate Levels** - Use debug for development, info for important events, warn for issues, error for failures
3. **Structured Data** - Pass objects with relevant context
4. **No Sensitive Data** - Never log passwords, tokens, or PII
5. **Production Ready** - Logs should be helpful for production troubleshooting

## Emergency Debugging Checklist

When debugging production issues:

1. ✅ Enable debug: `__logger.enableDebug()`
2. ✅ Set appropriate namespace: `__logger.enableNamespace('api', 'auth')`
3. ✅ Set log level: `__logger.setLevel('debug')`
4. ✅ Reproduce the issue
5. ✅ Check session info: `__logger.getStatus()`
6. ✅ Clear settings when done: `__logger.clearDebugSettings()`

The logger will automatically add session IDs and timestamps when debugging in production to help correlate logs across user sessions.