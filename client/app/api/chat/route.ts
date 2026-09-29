export async function POST(req: Request) {
  try {
    const { messages, workspaceId, threadId, assistantId } = await req.json()
    
    // Get the last message content
    const lastMessage = messages[messages.length - 1]
    if (!lastMessage || lastMessage.role !== 'user') {
      return new Response('Invalid message format', { status: 400 })
    }

    // Use the streaming endpoint
    const streamingUrl = `${process.env.MCP_SERVER_URL || 'http://localhost:8090'}/admin/api/v1/workspaces/${workspaceId}/assistants/threads/${threadId}/chat`

    // Get auth token from cookie
    const cookieHeader = req.headers.get('cookie') || ''
    const cookies = cookieHeader.split(';').map(c => c.trim())
    const authCookie = cookies.find(c => c.startsWith('auth-token='))
    const authToken = authCookie ? authCookie.split('=')[1] : null

    const response = await fetch(streamingUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
      },
      body: JSON.stringify({
        content: lastMessage.content
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Backend responded with ${response.status}: ${errorText}`)
    }

    // Create a transform stream that converts backend SSE to Vercel AI format
    const encoder = new TextEncoder()
    const decoder = new TextDecoder()
    
    const stream = new ReadableStream({
      async start(controller) {
        const reader = response.body!.getReader()
        let buffer = ''
        
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            
            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6).trim()
                
                if (data === '[DONE]') {
                  // Send a final newline to ensure the stream ends properly
                  controller.enqueue(encoder.encode('\n'))
                  controller.close()
                  return
                }
                
                if (data) {
                  try {
                    const event = JSON.parse(data)
                    
                    // Only process assistant messages
                    if (event.type === 'message' && event.data.role === 'assistant' && event.data.content) {
                      // For streaming, send the content in small chunks
                      const content = event.data.content
                      const words = content.split(' ')
                      
                      for (let i = 0; i < words.length; i++) {
                        const word = words[i] + (i < words.length - 1 ? ' ' : '')
                        controller.enqueue(encoder.encode(word))
                        // Add a small delay for streaming effect
                        await new Promise(resolve => setTimeout(resolve, 20))
                      }
                    }
                  } catch (e) {
                  }
                }
              }
            }
          }
        } catch (error) {
          controller.error(error)
        }
      }
    })

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    })
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }), 
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    )
  }
}