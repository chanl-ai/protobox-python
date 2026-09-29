/**
 * API Call Logger - Debug tool to track all API calls and identify races
 */

interface APICall {
  id: string
  url: string
  method: string
  timestamp: number
  caller: string
  status?: number
  duration?: number
}

class APICallLogger {
  private calls: APICall[] = []
  private enabled = process.env.NODE_ENV === 'development'

  log(url: string, method: string = 'GET', caller: string = 'unknown') {
    if (!this.enabled) return null

    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const call: APICall = {
      id,
      url,
      method,
      timestamp: Date.now(),
      caller: this.getCaller(caller)
    }
    
    this.calls.push(call)
    
    if (typeof window !== 'undefined' && window.console) {
      window.console.group(`🌐 API Call: ${method} ${url}`)
      window.console.log('Caller:', call.caller)
      window.console.log('Timestamp:', new Date(call.timestamp).toISOString())
      window.console.log('Call ID:', id)
      window.console.groupEnd()
    }
    
    return id
  }

  complete(id: string, status: number, duration?: number) {
    if (!this.enabled || !id) return

    const call = this.calls.find(c => c.id === id)
    if (call) {
      call.status = status
      call.duration = duration
      
      const statusColor = status >= 200 && status < 300 ? '✅' : '❌'
      if (typeof window !== 'undefined' && window.console) {
        window.console.log(`${statusColor} API Complete: ${call.method} ${call.url} (${status}) ${duration ? `in ${duration}ms` : ''}`)
      }
    }
  }

  getDuplicateCalls(timeWindow: number = 5000): APICall[][] {
    const groups: { [key: string]: APICall[] } = {}
    
    this.calls.forEach(call => {
      const key = `${call.method}:${call.url}`
      if (!groups[key]) groups[key] = []
      groups[key].push(call)
    })
    
    return Object.values(groups).filter(group => {
      if (group.length < 2) return false
      
      // Check if calls happened within time window
      group.sort((a, b) => a.timestamp - b.timestamp)
      const first = group[0].timestamp
      const last = group[group.length - 1].timestamp
      return (last - first) <= timeWindow
    })
  }

  getRacingCalls(): APICall[][] {
    return this.getDuplicateCalls(1000) // Calls within 1 second are likely racing
  }

  printReport() {
    if (!this.enabled || typeof window === 'undefined' || !window.console) return

    window.console.group('📊 API Call Report')
    window.console.log('Total calls:', this.calls.length)
    
    const racing = this.getRacingCalls()
    if (racing.length > 0) {
      window.console.group('⚠️ Racing calls detected!')
      racing.forEach(group => {
        window.console.group(`${group[0].method} ${group[0].url} (${group.length} calls)`)
        group.forEach(call => {
          window.console.log(`- ${new Date(call.timestamp).toISOString()} by ${call.caller}`)
        })
        window.console.groupEnd()
      })
      window.console.groupEnd()
    }
    
    const duplicates = this.getDuplicateCalls()
    if (duplicates.length > 0) {
      window.console.group('🔄 Duplicate calls (within 5s)')
      duplicates.forEach(group => {
        window.console.log(`${group[0].method} ${group[0].url}: ${group.length} calls`)
      })
      window.console.groupEnd()
    }
    
    window.console.groupEnd()
  }

  private getCaller(fallback: string): string {
    try {
      const stack = new Error().stack
      if (!stack) return fallback
      
      const lines = stack.split('\n')
      // Skip Error, getCaller, log, and the calling function
      const relevantLine = lines[4] || lines[3] || lines[2]
      
      if (relevantLine) {
        // Extract function name and file
        const match = relevantLine.match(/at\s+(.+?)\s+\((.+):(\d+):(\d+)\)/)
        if (match) {
          const [, func, file, line] = match
          const fileName = file.split('/').pop()
          return `${func} (${fileName}:${line})`
        }
      }
      
      return fallback
    } catch {
      return fallback
    }
  }

  clear() {
    this.calls = []
  }
}

export const apiLogger = new APICallLogger()

// Make it available globally for debugging
if (typeof window !== 'undefined') {
  (window as any).apiLogger = apiLogger
  (window as any).printAPIReport = () => apiLogger.printReport()
}