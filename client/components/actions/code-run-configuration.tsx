"use client"

import { useState, useEffect } from "react"
import dynamic from "next/dynamic"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Trash2, Plus, Code2, FolderOpen, FileText, Play, Settings, Edit3, Save, X } from "lucide-react"

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  loading: () => <div className="flex items-center justify-center h-64 bg-muted/20 rounded">Loading editor...</div>,
  ssr: false
})

interface CodeFile {
  name: string
  content: string
  language: string
}

// Helper function to safely extract string from potentially complex objects
const safeString = (value: any): string => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number') return String(value)
  if (typeof value === 'object') {
    // Handle common object patterns
    if (value.value) return String(value.value)
    if (value.label) return String(value.label)
    if (value.name) return String(value.name)
    if (value.toString && typeof value.toString === 'function') return value.toString()
    return JSON.stringify(value)
  }
  return String(value)
}

interface CodeRunConfigurationProps {
  form: any // We'll type this properly later
}

// Simple test components to isolate the error
function TestComponent1() {
  return <div>Test Component 1 - Basic div</div>
}

function TestComponent2({ form }: { form: any }) {
  return (
    <div>
      Test Component 2 - Form watch: {String(form.watch("config.language") || "python")}
    </div>
  )
}

function TestComponent3() {
  const files = [{ name: "main.py", content: "test", language: "python" }]
  return (
    <div>
      Test Component 3 - Files length: {files.length}
    </div>
  )
}

export function CodeRunConfiguration({ form }: CodeRunConfigurationProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Code Run Configuration - Component Testing</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <TestComponent1 />
            <TestComponent2 form={form} />
            <TestComponent3 />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}