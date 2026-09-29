"use client"

import { 
  ArrowUp, 
  Square, 
  Paperclip, 
  Plus, 
  ChevronDown, 
  User, 
  Bot, 
  ThumbsUp, 
  ThumbsDown, 
  Copy,
  type LucideIcon 
} from "lucide-react"

const iconMap: Record<string, LucideIcon> = {
  "arrow-up": ArrowUp,
  "square": Square,
  "paperclip": Paperclip,
  "plus": Plus,
  "chevron-down": ChevronDown,
  "user": User,
  "bot": Bot,
  "thumbs-up": ThumbsUp,
  "thumbs-down": ThumbsDown,
  "copy": Copy,
}

interface DynamicIconProps {
  name: keyof typeof iconMap
  className?: string
}

export function DynamicIcon({ name, className }: DynamicIconProps) {
  const IconComponent = iconMap[name]
  
  if (!IconComponent) {
    return null
  }
  
  return <IconComponent className={className} />
}