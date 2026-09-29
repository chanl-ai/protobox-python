import React from 'react'
import Image from 'next/image'

export const ClaudeIcon = ({ className = "h-4 w-4" }: { className?: string }) => (
  <Image 
    src="/images/claude-logo.svg" 
    alt="Claude" 
    width={16}
    height={16}
    className={className}
  />
)

export const CursorIcon = ({ className = "h-4 w-4" }: { className?: string }) => (
  <Image 
    src="/images/cursor-logo.svg" 
    alt="Cursor" 
    width={16}
    height={16}
    className={className}
  />
)

export const ChatGPTIcon = ({ className = "h-4 w-4" }: { className?: string }) => (
  <Image 
    src="/images/chatgpt-logo.svg" 
    alt="ChatGPT"
    width={16}
    height={16} 
    className={className}
  />
)