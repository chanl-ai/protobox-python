"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { 
  Download, 
  Copy, 
  Check, 
  FileText, 
  Code, 
  Settings,
  Loader2
} from "lucide-react"
import { toast } from "sonner"

interface ExportPromptDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  prompt: {
    id: string
    name: string
    description: string
    category: string
    tags: string[]
    messages: any[]
    arguments: any[]
    is_active: boolean
  }
}

type ExportFormat = "json" | "yaml" | "markdown" | "text"

export function ExportPromptDialog({ open, onOpenChange, prompt }: ExportPromptDialogProps) {
  const [exportFormat, setExportFormat] = useState<ExportFormat>("json")
  const [exportedContent, setExportedContent] = useState<string>("")
  const [isExporting, setIsExporting] = useState(false)
  const [copied, setCopied] = useState(false)

  const exportPrompt = async () => {
    setIsExporting(true)
    try {
      // TODO: Replace with actual API call when backend supports export
      // const response = await promptsApi.exportPrompt(prompt.id, exportFormat)
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500))
      
      let content = ""
      
      switch (exportFormat) {
        case "json":
          content = JSON.stringify({
            name: prompt.name,
            description: prompt.description,
            category: prompt.category,
            tags: prompt.tags,
            is_active: prompt.is_active,
            messages: prompt.messages,
            arguments: prompt.arguments,
            exported_at: new Date().toISOString(),
            version: "1.0.0"
          }, null, 2)
          break
          
        case "yaml":
          content = `name: ${prompt.name}
description: ${prompt.description}
category: ${prompt.category}
tags:
${prompt.tags.map(tag => `  - ${tag}`).join('\n')}
is_active: ${prompt.is_active}
messages:
${prompt.messages.map(msg => `  - role: ${msg.role}\n    content: |\n      ${msg.content.replace(/\n/g, '\n      ')}`).join('\n')}
arguments:
${prompt.arguments.map(arg => `  - name: ${arg.name}\n    description: ${arg.description}\n    type: ${arg.type}\n    required: ${arg.required}`).join('\n')}
exported_at: ${new Date().toISOString()}
version: "1.0.0"`
          break
          
        case "markdown":
          content = `# ${prompt.name}

**Description:** ${prompt.description}

**Category:** ${prompt.category}

**Tags:** ${prompt.tags.join(', ')}

**Status:** ${prompt.is_active ? 'Active' : 'Inactive'}

## Messages

${prompt.messages.map((msg, index) => `### ${msg.role.charAt(0).toUpperCase() + msg.role.slice(1)} Message ${index + 1}

\`\`\`
${msg.content}
\`\`\``).join('\n\n')}

## Arguments

${prompt.arguments.length > 0 ? prompt.arguments.map(arg => `- **${arg.name}** (${arg.type})${arg.required ? ' *required*' : ''}: ${arg.description}`).join('\n') : 'No arguments defined'}

---

*Exported on ${new Date().toLocaleString()}*`
          break
          
        case "text":
          content = `PROMPT: ${prompt.name}
DESCRIPTION: ${prompt.description}
CATEGORY: ${prompt.category}
TAGS: ${prompt.tags.join(', ')}
STATUS: ${prompt.is_active ? 'Active' : 'Inactive'}

MESSAGES:
${prompt.messages.map((msg, index) => `${index + 1}. [${msg.role.toUpperCase()}]\n${msg.content}\n`).join('\n')}

ARGUMENTS:
${prompt.arguments.length > 0 ? prompt.arguments.map(arg => `- ${arg.name} (${arg.type})${arg.required ? ' *required*' : ''}: ${arg.description}`).join('\n') : 'No arguments defined'}

Exported: ${new Date().toLocaleString()}`
          break
      }
      
      setExportedContent(content)
      toast.success("Prompt exported successfully")
    } catch (error) {
      toast.error("Failed to export prompt")
    } finally {
      setIsExporting(false)
    }
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(exportedContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      toast.success("Copied to clipboard")
    } catch (error) {
      toast.error("Failed to copy to clipboard")
    }
  }

  const downloadFile = () => {
    const blob = new Blob([exportedContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${prompt.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.${exportFormat === 'text' ? 'txt' : exportFormat}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success("File downloaded")
  }

  const getFormatIcon = (format: ExportFormat) => {
    switch (format) {
      case "json":
        return <Code className="h-4 w-4" />
      case "yaml":
        return <Settings className="h-4 w-4" />
      case "markdown":
        return <FileText className="h-4 w-4" />
      case "text":
        return <FileText className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export Prompt: {prompt.name}
          </DialogTitle>
          <DialogDescription>
            Export your prompt in various formats for sharing or backup
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Prompt Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{prompt.name}</CardTitle>
              <CardDescription>{prompt.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">{prompt.category}</Badge>
                {prompt.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">{tag}</Badge>
                ))}
                <Badge variant={prompt.is_active ? "default" : "secondary"}>
                  {prompt.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Export Format Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Export Format</CardTitle>
              <CardDescription>
                Choose the format for exporting your prompt
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RadioGroup value={exportFormat} onValueChange={(value) => setExportFormat(value as ExportFormat)}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="json" id="json" />
                  <Label htmlFor="json" className="flex items-center gap-2">
                    {getFormatIcon("json")}
                    JSON - Complete data structure
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="yaml" id="yaml" />
                  <Label htmlFor="yaml" className="flex items-center gap-2">
                    {getFormatIcon("yaml")}
                    YAML - Human-readable configuration
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="markdown" id="markdown" />
                  <Label htmlFor="markdown" className="flex items-center gap-2">
                    {getFormatIcon("markdown")}
                    Markdown - Documentation format
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="text" id="text" />
                  <Label htmlFor="text" className="flex items-center gap-2">
                    {getFormatIcon("text")}
                    Plain Text - Simple format
                  </Label>
                </div>
              </RadioGroup>
            </CardContent>
          </Card>

          {/* Export Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Export Actions</CardTitle>
              <CardDescription>
                Generate and download the exported content
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button onClick={exportPrompt} disabled={isExporting} className="w-full">
                {isExporting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Export Prompt
                  </>
                )}
              </Button>
              
              {exportedContent && (
                <div className="space-y-4">
                  <Separator />
                  <div className="flex gap-2">
                    <Button variant="outline" onClick={copyToClipboard} disabled={copied}>
                      {copied ? (
                        <>
                          <Check className="h-4 w-4 mr-2" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-2" />
                          Copy to Clipboard
                        </>
                      )}
                    </Button>
                    <Button variant="outline" onClick={downloadFile}>
                      <Download className="h-4 w-4 mr-2" />
                      Download File
                    </Button>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Exported Content:</Label>
                    <Textarea
                      value={exportedContent}
                      readOnly
                      className="min-h-[200px] font-mono text-sm"
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
