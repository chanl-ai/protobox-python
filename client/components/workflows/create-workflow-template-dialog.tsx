"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Card, CardHeader } from "@/components/ui/card"
import { 
  Workflow, 
  Search, 
  Filter, 
  Zap, 
  Database, 
  Mail, 
  Calendar, 
  BarChart3,
  Clock,
  Users,
  FileText,
  Globe,
  Plus
} from "lucide-react"

interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: string
  difficulty: "beginner" | "intermediate" | "advanced"
  estimatedTime: string
  tags: string[]
  icon: React.ComponentType<{ className?: string }>
  preview: string
}

const workflowTemplates: WorkflowTemplate[] = [
  {
    id: "daily-data-sync",
    name: "Daily Data Sync",
    description: "Automatically sync data from external APIs and databases on a daily schedule",
    category: "data-sync",
    difficulty: "intermediate",
    estimatedTime: "15-30 min",
    tags: ["automation", "data", "daily", "sync"],
    icon: Database,
    preview: "This workflow will automatically fetch data from configured sources, transform it according to your rules, and store it in your database."
  },
  {
    id: "email-notifications",
    name: "Email Notifications",
    description: "Send automated email notifications based on triggers and conditions",
    category: "notifications",
    difficulty: "beginner",
    estimatedTime: "10-20 min",
    tags: ["email", "notifications", "automation"],
    icon: Mail,
    preview: "Configure email templates and triggers to automatically send notifications when specific events occur in your system."
  },
  {
    id: "weekly-reports",
    name: "Weekly Reports",
    description: "Generate and distribute weekly performance reports automatically",
    category: "reporting",
    difficulty: "intermediate",
    estimatedTime: "20-40 min",
    tags: ["reports", "weekly", "analytics", "automation"],
    icon: BarChart3,
    preview: "Automatically collect data, generate insights, and distribute reports to stakeholders on a weekly schedule."
  },
  {
    id: "user-onboarding",
    name: "User Onboarding",
    description: "Automated user onboarding workflow with welcome emails and setup tasks",
    category: "user-management",
    difficulty: "beginner",
    estimatedTime: "15-25 min",
    tags: ["onboarding", "users", "automation", "welcome"],
    icon: Users,
    preview: "Streamline user onboarding with automated welcome messages, setup guides, and follow-up communications."
  },
  {
    id: "data-backup",
    name: "Data Backup",
    description: "Automated data backup and archiving workflow",
    category: "maintenance",
    difficulty: "intermediate",
    estimatedTime: "25-45 min",
    tags: ["backup", "data", "maintenance", "automation"],
    icon: Database,
    preview: "Automatically backup critical data, verify integrity, and archive old backups according to your retention policy."
  },
  {
    id: "api-monitoring",
    name: "API Monitoring",
    description: "Monitor API endpoints and trigger alerts on failures",
    category: "monitoring",
    difficulty: "advanced",
    estimatedTime: "30-60 min",
    tags: ["monitoring", "api", "alerts", "automation"],
    icon: Globe,
    preview: "Continuously monitor your API endpoints, track performance metrics, and automatically alert teams when issues are detected."
  },
  {
    id: "document-processing",
    name: "Document Processing",
    description: "Automated document processing and classification workflow",
    category: "content",
    difficulty: "advanced",
    estimatedTime: "40-80 min",
    tags: ["documents", "processing", "ai", "automation"],
    icon: FileText,
    preview: "Automatically process incoming documents, extract key information, classify content, and route to appropriate teams."
  },
  {
    id: "scheduled-tasks",
    name: "Scheduled Tasks",
    description: "Execute tasks on specific schedules with conditional logic",
    category: "automation",
    difficulty: "intermediate",
    estimatedTime: "20-35 min",
    tags: ["scheduling", "tasks", "automation", "logic"],
    icon: Clock,
    preview: "Create complex scheduling workflows that execute tasks based on time, conditions, and business rules."
  }
]

const categories = [
  { id: "data-sync", label: "Data Sync", icon: Database },
  { id: "notifications", label: "Notifications", icon: Mail },
  { id: "reporting", label: "Reporting", icon: BarChart3 },
  { id: "user-management", label: "User Management", icon: Users },
  { id: "maintenance", label: "Maintenance", icon: Zap },
  { id: "monitoring", label: "Monitoring", icon: Globe },
  { id: "content", label: "Content", icon: FileText },
  { id: "automation", label: "Automation", icon: Clock },
]

const difficulties = [
  { id: "beginner", label: "Beginner", color: "bg-green-100 text-green-800" },
  { id: "intermediate", label: "Intermediate", color: "bg-yellow-100 text-yellow-800" },
  { id: "advanced", label: "Advanced", color: "bg-red-100 text-red-800" },
]

interface CreateWorkflowTemplateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onTemplateSelect: (template: WorkflowTemplate) => void
}

export function CreateWorkflowTemplateDialog({
  open,
  onOpenChange,
  onTemplateSelect,
}: CreateWorkflowTemplateDialogProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [selectedDifficulties, setSelectedDifficulties] = useState<string[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null)

  const filteredTemplates = workflowTemplates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         template.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    
    const matchesCategory = selectedCategories.length === 0 || selectedCategories.includes(template.category)
    const matchesDifficulty = selectedDifficulties.length === 0 || selectedDifficulties.includes(template.difficulty)
    
    return matchesSearch && matchesCategory && matchesDifficulty
  })

  const handleCategoryToggle = (categoryId: string) => {
    setSelectedCategories(prev => 
      prev.includes(categoryId) 
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    )
  }

  const handleDifficultyToggle = (difficultyId: string) => {
    setSelectedDifficulties(prev => 
      prev.includes(difficultyId) 
        ? prev.filter(id => id !== difficultyId)
        : [...prev, difficultyId]
    )
  }

  const clearFilters = () => {
    setSelectedCategories([])
    setSelectedDifficulties([])
    setSearchQuery("")
  }

  const resetSelection = () => {
    setSelectedTemplate(null)
  }

  // Reset selection when dialog opens/closes
  useEffect(() => {
    if (open) {
      resetSelection()
    }
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl h-[80vh] flex flex-col">
        <DialogHeader className="border-b pb-4">
          <DialogTitle className="flex items-center gap-2">
            <Workflow className="h-5 w-5" />
            Create Workflow from Template
          </DialogTitle>
          <DialogDescription>
            Choose from our collection of pre-built workflow templates to get started quickly
          </DialogDescription>
        </DialogHeader>

                <div className="grid grid-cols-4 gap-6 flex-1 min-h-0">
          {/* Left Column - Filters */}
          <div className="min-h-0">
            <ScrollArea className="h-full">
              <div className="space-y-6 pr-4">
                <div>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search templates..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={clearFilters}
                    >
                      Clear
                    </Button>
                  </div>
                </div>

            <div>
              <Label className="text-sm font-medium mb-3 block">Categories</Label>
              <div className="space-y-2">
                {categories.map((category) => (
                  <div key={category.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`category-${category.id}`}
                      checked={selectedCategories.includes(category.id)}
                      onCheckedChange={() => handleCategoryToggle(category.id)}
                    />
                    <Label htmlFor={`category-${category.id}`} className="text-sm flex items-center gap-2">
                      <category.icon className="h-4 w-4" />
                      {category.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <Label className="text-sm font-medium mb-3 block">Difficulty Level</Label>
              <div className="space-y-2">
                {difficulties.map((difficulty) => (
                  <div key={difficulty.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`difficulty-${difficulty.id}`}
                      checked={selectedDifficulties.includes(difficulty.id)}
                      onCheckedChange={() => handleDifficultyToggle(difficulty.id)}
                    />
                    <Label htmlFor={`difficulty-${difficulty.id}`} className="text-sm">
                      {difficulty.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

                          </div>
            </ScrollArea>
          </div>

          {/* Right Column - Template Cards */}
          <div className="col-span-3 min-h-0">
            <ScrollArea className="h-full">
              <div className="grid grid-cols-2 gap-4 px-4">
                {filteredTemplates.map((template) => (
                  <Card 
                    key={template.id} 
                    className={`group hover:border-primary/50 transition-colors cursor-pointer ${
                      selectedTemplate?.id === template.id ? 'border-primary ring-2 ring-primary/20' : ''
                    }`}
                    onClick={() => setSelectedTemplate(template)}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0">
                          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                            <template.icon className="h-5 w-5 text-primary" />
                          </div>
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between mb-2">
                            <h3 className="font-medium text-base group-hover:text-primary transition-colors">
                              {template.name}
                            </h3>
                            <Badge 
                              variant="outline" 
                              className={difficulties.find(d => d.id === template.difficulty)?.color}
                            >
                              {template.difficulty}
                            </Badge>
                          </div>
                          
                          <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                            {template.description}
                          </p>
                          
                          <div className="flex items-center gap-3 text-xs text-muted-foreground mb-2">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {template.estimatedTime}
                            </span>
                            <span className="flex items-center gap-1">
                              <Zap className="h-3 w-3" />
                              {template.category}
                            </span>
                          </div>
                          
                          <div className="flex flex-wrap gap-1">
                            {template.tags.slice(0, 3).map((tag) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                            {template.tags.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{template.tags.length - 3}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* Dialog Footer */}
        <div className="border-t pt-4 mt-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Showing {filteredTemplates.length} of {workflowTemplates.length} templates
            </div>
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button 
                variant="default" 
                onClick={() => selectedTemplate && onTemplateSelect(selectedTemplate)}
                disabled={!selectedTemplate}
              >
                <Plus className="h-4 w-4 mr-2" />
                Use Selected Template
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
