# Secure Docker Code Executor

A production-ready, security-hardened Docker container for executing untrusted code in a sandboxed environment.

## 🔒 Security Features

This implementation follows industry best practices for running untrusted code:

### Container Security
- **Non-root execution**: Runs as unprivileged user (UID 1001)
- **Read-only filesystem**: Prevents malicious file modifications
- **Minimal base image**: Alpine Linux reduces attack surface
- **Multi-stage build**: Excludes build tools from final image
- **Resource limits**: CPU, memory, and process restrictions
- **Network isolation**: No external network access by default

### System Security
- **Capabilities dropped**: Removes all Linux capabilities, adds only necessary ones
- **No privilege escalation**: `no-new-privileges` flag prevents setuid abuse
- **Seccomp profile**: Custom syscall filtering
- **AppArmor/SELinux**: Mandatory access control
- **Temporary filesystems**: tmpfs mounts with security flags

### Application Security
- **Input validation**: Strict limits on code size, execution time, memory
- **Import restrictions**: Whitelist-based module imports
- **Process isolation**: Subprocess execution with clean environment
- **Resource monitoring**: Real-time CPU and memory tracking
- **Timeout enforcement**: Hard limits prevent infinite loops

## 🚀 Quick Start

### Local Development

1. **Build and run with security hardening:**

```bash
cd docker/code-executor
docker-compose -f docker-compose.local.yml up --build
```

2. **Test the service:**

```bash
curl -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "output = sum([1, 2, 3, 4, 5])",
    "timeout": 10
  }'
```

### Production Deployment (Fly.io)

1. **Install Fly CLI and deploy:**

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
fly apps create mcp-code-executor
fly deploy --config docker/code-executor/fly.toml
```

## 📋 API Reference

### Execute Code

**POST** `/execute`

```json
{
  "code": "output = 'Hello, World!'",
  "language": "python",
  "timeout": 30,
  "memory_limit_mb": 256,
  "allowed_imports": ["json", "math", "datetime"],
  "entry_point": "output",
  "input_data": {}
}
```

**Response:**

```json
{
  "success": true,
  "result": {"output": "Hello, World!"},
  "error_message": null,
  "execution_time_ms": 150,
  "memory_usage_mb": 12,
  "exit_code": 0,
  "stdout": "",
  "stderr": ""
}
```

## 🛡️ Security Considerations

### Threat Model

This setup protects against:

- **Code injection attacks**: Sandboxed execution environment
- **Resource exhaustion**: Strict CPU, memory, process limits  
- **Container escape**: Non-root user, dropped capabilities, seccomp
- **Network attacks**: Isolated network, no external access
- **File system attacks**: Read-only filesystem, restricted tmpfs
- **Privilege escalation**: No-new-privileges, minimal capabilities

### Monitoring & Alerting

Monitor these security indicators:

- **Execution failures**: High error rates may indicate attacks
- **Resource usage**: Unusual CPU/memory patterns
- **Timeout events**: Potential infinite loop attacks  
- **Network attempts**: Blocked connection attempts
- **File system violations**: Write attempts to read-only areas 