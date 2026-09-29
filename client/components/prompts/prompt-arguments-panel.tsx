"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Trash2, Plus, Edit2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { PromptArgument } from "@/lib/api/prompts"

// Schema for argument form validation
const argumentFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(50, "Name must be less than 50 characters"),
  description: z.string().max(200, "Description must be less than 200 characters").optional().default(""),
  type: z.enum(['string', 'number', 'boolean', 'array', 'object']).default('string'),
  required: z.boolean().default(false),
  default: z.any().optional(),
})

type ArgumentFormData = z.infer<typeof argumentFormSchema>

// Smart defaults based on argument name patterns
const getSmartDefaults = (name: string): Partial<PromptArgument> => {
  const lowerName = name.toLowerCase()
  
  // Boolean patterns
  if (lowerName.includes('flag') || lowerName.includes('enable') || lowerName.includes('disable') || 
      lowerName.includes('is_') || lowerName.includes('has_') || lowerName.includes('show') ||
      lowerName.includes('hide') || lowerName.includes('active')) {
    return {
      type: 'boolean',
      description: `Boolean flag for ${name.replace(/_/g, ' ')}`,
      default: false
    }
  }
  
  // Number patterns
  if (lowerName.includes('count') || lowerName.includes('limit') || lowerName.includes('max') ||
      lowerName.includes('min') || lowerName.includes('size') || lowerName.includes('length') ||
      lowerName.includes('number') || lowerName.includes('amount') || lowerName.includes('quantity')) {
    return {
      type: 'number',
      description: `Numeric value for ${name.replace(/_/g, ' ')}`,
      default: lowerName.includes('limit') || lowerName.includes('max') ? 10 : 1
    }
  }
  
  // Array patterns
  if (lowerName.includes('list') || lowerName.includes('items') || lowerName.includes('tags') ||
      lowerName.includes('options') || lowerName.endsWith('s') && !lowerName.endsWith('ss')) {
    return {
      type: 'array',
      description: `Array of ${name.replace(/_/g, ' ').replace(/s$/, '')} items`,
      default: []
    }
  }
  
  // Object patterns
  if (lowerName.includes('config') || lowerName.includes('settings') || lowerName.includes('params') ||
      lowerName.includes('options') && !lowerName.includes('list')) {
    return {
      type: 'object',
      description: `Configuration object for ${name.replace(/_/g, ' ')}`,
      default: {}
    }
  }
  
  // String patterns (default)
  const isRequired = lowerName.includes('required') || lowerName.includes('name') || 
                    lowerName.includes('id') || lowerName.includes('key')
  
  return {
    type: 'string',
    description: `Text input for ${name.replace(/_/g, ' ')}`,
    required: isRequired,
    default: isRequired ? undefined : ''
  }
}

interface PromptArgumentsPanelProps {
  arguments: PromptArgument[]
  onChange: (newArguments: PromptArgument[]) => void
  detectedArguments?: string[]
}

export function PromptArgumentsPanel({
  arguments: args,
  onChange,
  detectedArguments = []
}: PromptArgumentsPanelProps) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingArgument, setEditingArgument] = useState<PromptArgument | null>(null)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  
  const form = useForm<ArgumentFormData>({
    resolver: zodResolver(argumentFormSchema),
    defaultValues: {
      name: '',
      description: '',
      type: 'string',
      required: false,
      default: undefined,
    },
  })

  const addArgument = (name?: string) => {
    const argName = name || `arg_${args.length + 1}`
    const smartDefaults = name ? getSmartDefaults(name) : {}
    
    const newArg: PromptArgument = {
      name: argName,
      description: smartDefaults.description || "",
      type: smartDefaults.type || "string",
      required: smartDefaults.required || false,
      default: smartDefaults.default
    }
    
    setEditingArgument(newArg)
    setEditingIndex(args.length)
    
    // Pre-populate form with smart defaults
    form.reset({
      name: newArg.name,
      description: newArg.description,
      type: newArg.type,
      required: newArg.required,
      default: newArg.default || (newArg.type === 'boolean' ? false : newArg.type === 'number' ? 0 : '')
    })
    
    setDialogOpen(true)
  }

  const editArgument = (index: number) => {
    const arg = args[index]
    setEditingArgument(arg)
    setEditingIndex(index)
    
    form.reset({
      name: arg.name,
      description: arg.description,
      type: arg.type,
      required: arg.required,
      default: arg.default || (arg.type === 'boolean' ? false : arg.type === 'number' ? 0 : '')
    })
    
    setDialogOpen(true)
  }
  
  const handleFormSubmit = (data: ArgumentFormData) => {
    const updatedArg: PromptArgument = {
      name: data.name,
      description: data.description || '',
      type: data.type,
      required: data.required,
      default: data.default === '' ? undefined : data.default
    }
    
    let updated: PromptArgument[]
    if (editingIndex !== null && editingIndex < args.length) {
      // Update existing argument
      updated = args.map((arg, i) => i === editingIndex ? updatedArg : arg)
    } else {
      // Add new argument
      updated = [...args, updatedArg]
    }
    
    onChange(updated)
    setDialogOpen(false)
    setEditingArgument(null)
    setEditingIndex(null)
  }
  
  const handleDialogClose = () => {
    setDialogOpen(false)
    setEditingArgument(null)
    setEditingIndex(null)
    form.reset()
  }

  const addDetectedArgument = (name: string) => {
    if (!args.find(arg => arg.name === name)) {
      const smartDefaults = getSmartDefaults(name)
      const newArg: PromptArgument = {
        name: name,
        description: smartDefaults.description || `Parameter for ${name.replace(/_/g, ' ')}`,
        type: smartDefaults.type || "string",
        required: smartDefaults.required || false,
        default: smartDefaults.default !== undefined ? smartDefaults.default : (
          smartDefaults.type === 'boolean' ? false : 
          smartDefaults.type === 'number' ? 0 : 
          smartDefaults.type === 'array' ? [] :
          smartDefaults.type === 'object' ? {} : ''
        )
      }
      
      // Add directly to the list with complete metadata
      const updated = [...args, newArg]
      onChange(updated)
    }
  }

  return (
    <>
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Arguments</CardTitle>
          <Button onClick={() => addArgument()} size="sm" variant="outline">
            <Plus className="h-4 w-4 mr-1" />
            Add
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Detected Arguments */}
        {detectedArguments.length > 0 && (
          <div className="pb-4 border-b">
            <Label className="text-sm font-medium mb-2 block">
              Detected in content:
            </Label>
            <div className="flex flex-wrap gap-2">
              {detectedArguments
                .filter(name => !args.find(arg => arg.name === name))
                .map(name => (
                  <Button
                    key={name}
                    variant="outline"
                    size="sm"
                    onClick={() => addDetectedArgument(name)}
                    className="text-xs"
                  >
                    + {name}
                  </Button>
                ))}
            </div>
          </div>
        )}

        {/* Arguments List */}
        {args.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            No arguments defined. Arguments are automatically created when you use {`{{variable_name}}`} in your prompt content.
          </p>
        ) : (
          <div className="space-y-3">
            {args.map((arg, index) => {
              const isOrphaned = detectedArguments.length > 0 && !detectedArguments.includes(arg.name)
              return (
              <div 
                key={index} 
                className={`border rounded-lg p-3 transition-all ${
                  isOrphaned ? 'border-orange-300 bg-orange-50/50' : ''
                }`}
              >
                {isOrphaned && (
                  <div className="text-xs text-orange-600 mb-2 flex items-center gap-1">
                    <span>⚠️</span>
                    <span>Not used in prompt content</span>
                  </div>
                )}
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-medium text-sm">{arg.name}</span>
                      <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                        {arg.type}
                      </span>
                      {arg.required && (
                        <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">
                          required
                        </span>
                      )}
                    </div>
                    {arg.description && (
                      <p className="text-xs text-muted-foreground mb-1 line-clamp-2">
                        {arg.description}
                      </p>
                    )}
                    {arg.default !== undefined && arg.default !== null && arg.default !== '' && (
                      <p className="text-xs text-muted-foreground">
                        Default: {String(arg.default)}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => editArgument(index)}
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-blue-600"
                      title="Edit argument properties"
                    >
                      <Edit2 className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        const updated = args.filter((_, i) => i !== index)
                        onChange(updated)
                      }}
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-red-600"
                      title="Remove argument"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
            )
            })}
          </div>
        )}
        
        {/* Helpful explanation */}
        {args.length > 0 && (
          <div className="mt-4 p-3 bg-muted/30 rounded-lg border">
            <p className="text-xs text-muted-foreground">
              💡 <strong>Tip:</strong> Arguments are automatically created from variables in your prompt content using the <code className="bg-muted px-1 rounded">{`{{variable_name}}`}</code> format. Edit them to customize types, descriptions, and default values.
            </p>
          </div>
        )}
      </CardContent>
      
      {/* Argument Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingArgument && editingIndex !== null && editingIndex < args.length
                ? 'Edit Argument'
                : 'Add Argument'}
            </DialogTitle>
            <DialogDescription>
              Configure the argument properties and validation rules.
            </DialogDescription>
          </DialogHeader>
          
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleFormSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="argument_name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea 
                        placeholder="Describe what this argument is used for..."
                        className="min-h-[80px] resize-none"
                        {...field} 
                      />
                    </FormControl>
                    <FormDescription>
                      Optional description to help users understand this argument
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Type</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="string">String</SelectItem>
                          <SelectItem value="number">Number</SelectItem>
                          <SelectItem value="boolean">Boolean</SelectItem>
                          <SelectItem value="array">Array</SelectItem>
                          <SelectItem value="object">Object</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="required"
                  render={({ field }) => (
                    <FormItem className="flex flex-col space-y-2">
                      <FormLabel>Required</FormLabel>
                      <FormControl>
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                          <span className="text-sm text-muted-foreground">
                            {field.value ? 'Required' : 'Optional'}
                          </span>
                        </div>
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
              
              <FormField
                control={form.control}
                name="default"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Default Value</FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="Optional default value"
                        {...field}
                        value={field.value || ''}
                      />
                    </FormControl>
                    <FormDescription>
                      Default value used when argument is not provided
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleDialogClose}>
                  Cancel
                </Button>
                <Button type="submit">
                  {editingArgument && editingIndex !== null && editingIndex < args.length
                    ? 'Update Argument'
                    : 'Add Argument'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </Card>
    </>
  )
}