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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Eye, Play, Copy, Check } from "lucide-react"
import { toast } from "sonner"

interface PromptMessage {
  role: "system" | "user" | "assistant"
  content: string
}

interface PromptArgument {
  name: string
  description: string
  type: "string" | "number" | "boolean" | "array" | "object"
  required: boolean
  default?: any
}

interface PreviewPromptDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  prompt?: {
    id: string
    name: string
    description: string
    messages: PromptMessage[]
    arguments: PromptArgument[]
    category: string
    tags: string[]
    is_active: boolean
  } | null
}

export function PreviewPromptDialog({ open, onOpenChange, prompt }: PreviewPromptDialogProps) {
  const [testArguments, setTestArguments] = useState<Record<string, any>>({})
  const [renderedMessages, setRenderedMessages] = useState<PromptMessage[]>([])
  const [isExecuting, setIsExecuting] = useState(false)
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  
  // Return early if prompt is null
  if (!prompt) {
    return null
  }

  const handleArgumentChange = (name: string, value: any) => {
    setTestArguments(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const executePrompt = async () => {
    setIsExecuting(true)
    try {
      // TODO: Replace with actual API call
      // const response = await promptsApi.executePrompt(prompt.id, { arguments: testArguments })
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Mock rendered messages - ensure messages array exists
      const messages = prompt.messages || []
      const mockRendered = messages.map(msg => ({
        ...msg,
        content: (msg.content || "").replace(/\{\{(\w+)\}\}/g, (match, key) => {
          return testArguments[key] || match
        })
      }))
      
      setRenderedMessages(mockRendered)
      toast.success("Prompt executed successfully")
    } catch (error) {
      toast.error("Failed to execute prompt")
    } finally {
      setIsExecuting(false)
    }
  }

  const copyToClipboard = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedIndex(index)
      setTimeout(() => setCopiedIndex(null), 2000)
      toast.success("Copied to clipboard")
    } catch (error) {
      toast.error("Failed to copy to clipboard")
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case "system":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
      case "user":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
      case "assistant":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300"
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Preview Prompt: {prompt.name}
          </DialogTitle>
          <DialogDescription>
            Test and preview how your prompt will be rendered with different arguments
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
              <div className="flex flex-wrap gap-2 mb-4">
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

          {/* Test Arguments */}
          {prompt.arguments && prompt.arguments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Test Arguments</CardTitle>
                <CardDescription>
                  Provide values for the prompt arguments to test the template
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {(prompt.arguments || []).map((arg) => (
                  <div key={arg.name} className="space-y-2">
                    <Label htmlFor={arg.name} className="flex items-center gap-2">
                      {arg.name}
                      {arg.required && <span className="text-red-500">*</span>}
                      <span className="text-sm text-muted-foreground">
                        ({arg.type})
                      </span>
                    </Label>
                    <p className="text-sm text-muted-foreground">{arg.description}</p>
                    {arg.type === "string" ? (
                      <Input
                        id={arg.name}
                        placeholder={arg.default || `Enter ${arg.name}`}
                        value={testArguments[arg.name] || ""}
                        onChange={(e) => handleArgumentChange(arg.name, e.target.value)}
                      />
                    ) : arg.type === "number" ? (
                      <Input
                        id={arg.name}
                        type="number"
                        placeholder={arg.default || `Enter ${arg.name}`}
                        value={testArguments[arg.name] || ""}
                        onChange={(e) => handleArgumentChange(arg.name, e.target.value)}
                      />
                    ) : arg.type === "boolean" ? (
                      <div className="flex items-center space-x-2">
                        <input
                          id={arg.name}
                          type="checkbox"
                          checked={testArguments[arg.name] || false}
                          onChange={(e) => handleArgumentChange(arg.name, e.target.checked)}
                        />
                        <Label htmlFor={arg.name}>Enable {arg.name}</Label>
                      </div>
                    ) : (
                      <Textarea
                        id={arg.name}
                        placeholder={arg.default || `Enter ${arg.name}`}
                        value={testArguments[arg.name] || ""}
                        onChange={(e) => handleArgumentChange(arg.name, e.target.value)}
                        rows={3}
                      />
                    )}
                  </div>
                ))}
                <Button onClick={executePrompt} disabled={isExecuting} className="w-full">
                  <Play className="h-4 w-4 mr-2" />
                  {isExecuting ? "Executing..." : "Execute Prompt"}
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Rendered Messages */}
          {renderedMessages.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Rendered Messages</CardTitle>
                <CardDescription>
                  How the prompt will look with your provided arguments
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {renderedMessages.map((message, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge className={getRoleColor(message.role)}>
                        {message.role.toUpperCase()}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(message.content, index)}
                      >
                        {copiedIndex === index ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <div className="p-3 bg-muted rounded-md">
                      <pre className="whitespace-pre-wrap text-sm">
                        {message.content}
                      </pre>
                    </div>
                    {index < renderedMessages.length - 1 && <Separator />}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
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
