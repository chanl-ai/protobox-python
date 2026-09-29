"use client"

import { ReactNode, createContext, useContext } from "react"
import { useForm, FormProvider as RHFFormProvider, UseFormReturn } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Action } from "@/lib/api/hooks"

// Form validation schemas
const headerSchema = z.object({
  key: z.string().min(1, "Header name is required"),
  value: z.string().min(1, "Header value is required"),
})

const inputVariableSchema = z.object({
  name: z.string().min(1, "Variable name is required"),
  description: z.string().min(1, "Variable description is required"),
  type: z.enum(["string", "number", "boolean"]).default("string"),
  required: z.boolean().default(true),
  default_value: z.string().optional()
})

const actionFormSchema = z.object({
  name: z.string()
    .min(1, "Action name is required")
    .max(255, "Name must be 255 characters or less")
    .regex(/^[a-zA-Z0-9\s\-_]+$/, "Name can only contain letters, numbers, spaces, hyphens, and underscores"),
  description: z.string()
    .min(10, "Description must be at least 10 characters")
    .max(1000, "Description must be 1000 characters or less"),
  type: z.enum(["REST", "DATABASE", "CODE_RUN", "KNOWLEDGE_BASE"]),
  tags: z.array(z.string()).default([]),
  version: z.string()
    .regex(/^\d+\.\d+\.\d+$/, "Version must follow semantic versioning (e.g., 1.0.0)"),
  
  // Input variables for LLM interaction
  inputVariables: z.array(inputVariableSchema).default([]),
  
  // REST API specific
  method: z.enum(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]).default("POST"),
  url: z.string().optional().or(z.literal("")),
  headers: z.array(headerSchema).default([]),
  bodyType: z.enum(["none", "json", "form", "text"]).default("json"),
  body: z.string().default(""),
  responseTransformation: z.string().default("{{response}}"),
  requestTransformation: z.string().optional().default(""),
  
  // CODE_RUN specific
  codeLanguage: z.enum(["python", "javascript", "sql", "shell"]).default("python"),
  sourceCode: z.string().default(""),
  executionTimeout: z.number().min(1).max(300).default(30),
  environmentVariables: z.record(z.string()).default({}),
  dependencies: z.array(z.string()).default([]),
  
  // Common
  secretRefs: z.array(z.string()).default([])
})

export type ActionFormData = z.infer<typeof actionFormSchema>

interface ActionFormContextType {
  action: Action
  form: UseFormReturn<ActionFormData>
}

const ActionFormContext = createContext<ActionFormContextType | null>(null)

export function useActionForm() {
  const context = useContext(ActionFormContext)
  if (!context) {
    throw new Error("useActionForm must be used within FormProvider")
  }
  return context
}

interface FormProviderProps {
  children: ReactNode
  action: Action
}

export function FormProvider({ children, action }: FormProviderProps) {
  const form = useForm<ActionFormData>({
    resolver: zodResolver(actionFormSchema),
    defaultValues: {
      name: action.name,
      description: action.description || "",
      type: action.type as any,
      tags: action.tags || [],
      version: action.version || "1.0.0",
      inputVariables: (action.config_schema as any)?.inputVariables || [],
      method: (action.default_config as any)?.method || "POST",
      url: (action.default_config as any)?.url || "",
      headers: [],
      bodyType: (action.default_config as any)?.bodyType || "json",
      body: (action.default_config as any)?.body || "",
      responseTransformation: (action.default_config as any)?.responseTransformation || "{{response}}",
      requestTransformation: (action.default_config as any)?.requestTransformation || "",
      codeLanguage: (action.default_config as any)?.codeLanguage || "python",
      sourceCode: (action.default_config as any)?.sourceCode || "",
      executionTimeout: (action.default_config as any)?.executionTimeout || 30,
      environmentVariables: (action.default_config as any)?.environmentVariables || {},
      dependencies: (action.default_config as any)?.dependencies || [],
      secretRefs: action.secret_refs || []
    }
  })

  return (
    <ActionFormContext.Provider value={{ action, form }}>
      <RHFFormProvider {...form}>
        <form className="space-y-6">
          {children}
        </form>
      </RHFFormProvider>
    </ActionFormContext.Provider>
  )
}