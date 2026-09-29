"use client"

import { useState } from "react"
import { Copy, Check, Download, ExternalLink, ChevronDown } from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast"
import Image from "next/image"

interface ClientCardProps {
  title: string
  description: string
  icon: string | React.ReactNode
  action?: {
    type: "copy" | "download" | "link"
    label: string
    value: string | (() => string)
    fileExtension?: string
  }
  helpText?: string
  languageSelector?: boolean
  languages?: string[]
  defaultLanguage?: string
  onViewDetails?: () => void
}

export function ClientCard({
  title,
  description,
  icon,
  action,
  helpText,
  languageSelector = false,
  languages = [".js", ".py", ".ts", ".go", ".java"],
  defaultLanguage = ".js",
  onViewDetails
}: ClientCardProps) {
  const { toast } = useToast()
  const [copied, setCopied] = useState(false)
  const [selectedLanguage, setSelectedLanguage] = useState(defaultLanguage)

  const handleCopy = async () => {
    if (!action) return
    
    const value = typeof action.value === "function" ? action.value() : action.value
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      toast({
        title: "Copied!",
        description: helpText || "Value copied to clipboard",
      })
    } catch (error) {
      toast({
        title: "Failed to copy",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const handleAction = () => {
    if (!action) return
    
    if (action.type === "copy") {
      handleCopy()
    } else if (action.type === "download") {
      // Handle download logic
      const value = typeof action.value === "function" ? action.value() : action.value
      const blob = new Blob([value], { type: "text/plain" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `protobox-mcp${action.fileExtension || ".txt"}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast({
        title: "Downloaded!",
        description: helpText || "File downloaded successfully",
      })
    }
  }

  const renderIcon = () => {
    if (typeof icon === "string") {
      return (
        <Image
          src={icon}
          alt=""
          width={20}
          height={20}
          className="object-contain"
        />
      )
    }
    return icon
  }

  const ActionIcon = !action ? Copy :
                     action.type === "copy" ? (copied ? Check : Copy) :
                     action.type === "download" ? Download :
                     ExternalLink

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-1">
        <div className="flex items-start gap-3">
          <div className="h-7 w-7 shrink-0 rounded bg-muted flex items-center justify-center">
            {renderIcon()}
          </div>
          <div className="space-y-1 flex-1">
            <h3 className="text-base font-medium leading-5">{title}</h3>
            <p className="text-sm text-muted-foreground leading-6">{description}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="border-t pt-4">
        <div className="w-full space-y-2">
          {onViewDetails ? (
            <Button 
              className="ms-auto" 
              variant="default"
              onClick={onViewDetails}
            >
              View Details
            </Button>
          ) : action ? (
            <div className="flex gap-2">
              {languageSelector && (
                <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {languages.map(lang => (
                      <SelectItem key={lang} value={lang}>{lang}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <div className="flex rounded-md shadow-sm flex-1">
                {action.type === "link" ? (
                  <a
                    href={typeof action.value === "function" ? action.value() : action.value}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1"
                  >
                    <Button className="w-full rounded-r-none" variant="default">
                      <span>{action.label}</span>
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </Button>
                  </a>
                ) : (
                  <Button
                    className="flex-1 rounded-r-none"
                    onClick={handleAction}
                    variant="default"
                  >
                    <span>{action.label}</span>
                  </Button>
                )}
                <Button
                  size="icon"
                  variant="default"
                  className="rounded-l-none border-l border-primary-foreground/20"
                  onClick={handleCopy}
                >
                  <ActionIcon className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : null}
          {helpText && (
            <p className="text-xs text-muted-foreground">{helpText}</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}