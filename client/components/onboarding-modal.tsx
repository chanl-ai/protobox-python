"use client"

import { useState } from 'react'
import { useAuth } from '@/lib/auth'
import { protoboxClient } from '@/lib/api/protobox-client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { toast } from 'sonner'
import { IconArrowLeft, IconArrowRight } from '@tabler/icons-react'

interface OnboardingModalProps {
  open: boolean
  onComplete: () => void
  workspaceId: string
  workspaceName: string
}

interface OnboardingData {
  // Workspace
  workspaceName: string
  industry: string
  teamSize: string
  // Preferences
  timezone: string
  language: string
  emailNotifications: boolean
  // AI Setup
  aiModel: string
  usageLimit: string
}

const INDUSTRIES = [
  { value: 'technology', label: 'Technology' },
  { value: 'finance', label: 'Finance' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'education', label: 'Education' },
  { value: 'retail', label: 'Retail' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'other', label: 'Other' },
]

const TEAM_SIZES = [
  { value: 'solo', label: 'Just me' },
  { value: 'small', label: '2-10 people' },
  { value: 'medium', label: '11-50 people' },
  { value: 'large', label: '50+ people' },
]

const TIMEZONES = [
  { value: 'America/New_York', label: 'Eastern Time (US)' },
  { value: 'America/Chicago', label: 'Central Time (US)' },
  { value: 'America/Denver', label: 'Mountain Time (US)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (US)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Paris', label: 'Central European Time' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEDT)' },
]

const AI_MODELS = [
  { value: 'gpt-4', label: 'GPT-4 (Most capable)' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo (Faster)' },
  { value: 'claude-2', label: 'Claude 2' },
]

const USAGE_LIMITS = [
  { value: '1000', label: '1,000 requests/month' },
  { value: '5000', label: '5,000 requests/month' },
  { value: '10000', label: '10,000 requests/month' },
  { value: 'unlimited', label: 'Unlimited (Enterprise)' },
]

export function OnboardingModal({ open, onComplete, workspaceId, workspaceName }: OnboardingModalProps) {
  const { user } = useAuth()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<OnboardingData>({
    workspaceName: workspaceName || '',
    industry: '',
    teamSize: 'solo',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/New_York',
    language: 'en',
    emailNotifications: true,
    aiModel: 'gpt-4',
    usageLimit: '1000',
  })

  const steps = [
    {
      title: 'Customize Your Workspace',
      description: "Let's set up your workspace",
    },
    {
      title: 'Your Preferences',
      description: 'Customize your experience',
    },
    {
      title: 'AI Configuration',
      description: 'Choose your AI preferences',
    },
  ]

  const updateData = (field: keyof OnboardingData, value: any) => {
    setData(prev => ({ ...prev, [field]: value }))
  }

  const handleNext = () => {
    if (currentStep === 0 && !data.workspaceName) {
      toast.error('Please enter a workspace name')
      return
    }
    
    if (currentStep < steps.length - 1) {
      setCurrentStep(prev => prev + 1)
    } else {
      handleComplete()
    }
  }

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1)
    }
  }

  const handleComplete = async () => {
    setLoading(true)
    
    try {
      if (!user?.customToken) {
        throw new Error('No authentication token available')
      }

      // Update existing workspace (not create new one)
      const updateResponse = await protoboxClient.updateWorkspace(workspaceId, {
        name: data.workspaceName,
        settings: {
          industry: data.industry,
          size: data.teamSize,
          aiModel: data.aiModel,
          apiLimits: {
            monthly: data.usageLimit === 'unlimited' ? -1 : parseInt(data.usageLimit),
          },
          needs_onboarding: false,  // Clear the flag
          auto_created: false,  // No longer auto-created after customization
        },
      })

      if (updateResponse.error) {
        throw new Error(updateResponse.error)
      }

      // Update user preferences
      const preferencesResponse = await protoboxClient.updateUserPreferences({
        timezone: data.timezone,
        language: data.language,
        emailNotifications: data.emailNotifications,
        onboardingCompleted: true,
      })

      if (preferencesResponse.error) {
      }

      toast.success('Workspace setup completed!')
      onComplete()
    } catch (error) {
      toast.error('Failed to complete setup. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="workspace-name">Workspace Name*</Label>
              <Input
                id="workspace-name"
                value={data.workspaceName}
                onChange={(e) => updateData('workspaceName', e.target.value)}
                placeholder="e.g., My Company"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="industry">Industry</Label>
              <Select value={data.industry} onValueChange={(value) => updateData('industry', value)}>
                <SelectTrigger id="industry">
                  <SelectValue placeholder="Select your industry" />
                </SelectTrigger>
                <SelectContent>
                  {INDUSTRIES.map(industry => (
                    <SelectItem key={industry.value} value={industry.value}>
                      {industry.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="team-size">Team Size</Label>
              <Select value={data.teamSize} onValueChange={(value) => updateData('teamSize', value)}>
                <SelectTrigger id="team-size">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TEAM_SIZES.map(size => (
                    <SelectItem key={size.value} value={size.value}>
                      {size.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )

      case 1:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Select value={data.timezone} onValueChange={(value) => updateData('timezone', value)}>
                <SelectTrigger id="timezone">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIMEZONES.map(tz => (
                    <SelectItem key={tz.value} value={tz.value}>
                      {tz.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="language">Language</Label>
              <Select value={data.language} onValueChange={(value) => updateData('language', value)}>
                <SelectTrigger id="language">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="es">Spanish</SelectItem>
                  <SelectItem value="fr">French</SelectItem>
                  <SelectItem value="de">German</SelectItem>
                  <SelectItem value="ja">Japanese</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="email-notifications"
                checked={data.emailNotifications}
                onCheckedChange={(checked) => updateData('emailNotifications', checked as boolean)}
              />
              <Label htmlFor="email-notifications" className="text-sm font-normal cursor-pointer">
                Send me email notifications about important updates
              </Label>
            </div>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ai-model">Preferred AI Model</Label>
              <Select value={data.aiModel} onValueChange={(value) => updateData('aiModel', value)}>
                <SelectTrigger id="ai-model">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AI_MODELS.map(model => (
                    <SelectItem key={model.value} value={model.value}>
                      {model.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="usage-limit">Monthly Usage Limit</Label>
              <Select value={data.usageLimit} onValueChange={(value) => updateData('usageLimit', value)}>
                <SelectTrigger id="usage-limit">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {USAGE_LIMITS.map(limit => (
                    <SelectItem key={limit.value} value={limit.value}>
                      {limit.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent 
        className="fixed inset-0 flex items-center justify-center p-0 max-w-none w-full h-full bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800" 
        onPointerDownOutside={(e) => e.preventDefault()}
      >
        <div className="w-full max-w-md">
          {/* Card container */}
          <div className="bg-card rounded-lg shadow-lg p-8">
            <DialogHeader>
              <div className="flex justify-between items-center mb-6">
                {steps.map((_, index) => (
                  <div
                    key={index}
                    className={`h-2 flex-1 rounded-full mx-1 transition-all duration-300 ${
                      index <= currentStep ? 'bg-primary' : 'bg-muted'
                    }`}
                  />
                ))}
              </div>
              <DialogTitle>{steps[currentStep].title}</DialogTitle>
              <DialogDescription>{steps[currentStep].description}</DialogDescription>
            </DialogHeader>

            <div className="py-4">
              {renderStepContent()}
            </div>

            <DialogFooter>
              <div className="flex justify-between w-full">
                <Button
                  variant="outline"
                  onClick={handleBack}
                  disabled={currentStep === 0 || loading}
                >
                  <IconArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button onClick={handleNext} disabled={loading}>
                  {currentStep === steps.length - 1 ? (
                    loading ? 'Saving...' : 'Complete Setup'
                  ) : (
                    <>
                      Continue
                      <IconArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            </DialogFooter>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}