"use client"

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { useCreateWorkspace } from '@/lib/api/hooks'
import { protoboxClient } from '@/lib/api/protobox-client'
import { OnboardingWizard, TextInput, SelectCards, WizardStep } from '@/components/onboarding/wizard'
import { SlugInput } from '@/components/ui/slug-input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { 
  IconBuildingStore,
  IconUser,
  IconCode,
  IconBriefcase,
  IconHeartHandshake,
  IconSchool,
  IconShoppingCart,
  IconTool,
  IconDots,
  IconUserCircle,
  IconUsers,
  IconUsersGroup,
  IconBuilding,
  IconRocket,
  IconBrain,
  IconBolt,
  IconSparkles,
  IconInfinity,
  IconPlug,
  IconMessages,
  IconWorld,
  IconMail,
  IconCheck
} from '@tabler/icons-react'
import { useAuthStore } from '@/lib/auth/stores/auth.store'

// Step data configurations
const TEAM_SIZES = [
  { value: 'solo', label: 'Just me', icon: <IconUserCircle className="h-5 w-5" />, description: 'Personal workspace' },
  { value: 'small', label: 'Small team', icon: <IconUsers className="h-5 w-5" />, description: '2-10 people' },
  { value: 'medium', label: 'Medium team', icon: <IconUsersGroup className="h-5 w-5" />, description: '11-50 people' },
  { value: 'large', label: 'Enterprise', icon: <IconBuilding className="h-5 w-5" />, description: '50+ people' },
]

const INDUSTRIES = [
  { value: 'technology', label: 'Technology', icon: <IconCode className="h-5 w-5" />, description: 'Software & IT' },
  { value: 'finance', label: 'Finance', icon: <IconBriefcase className="h-5 w-5" />, description: 'Banking & Investment' },
  { value: 'healthcare', label: 'Healthcare', icon: <IconHeartHandshake className="h-5 w-5" />, description: 'Medical & Health' },
  { value: 'education', label: 'Education', icon: <IconSchool className="h-5 w-5" />, description: 'Learning & Training' },
  { value: 'retail', label: 'Retail', icon: <IconShoppingCart className="h-5 w-5" />, description: 'E-commerce & Sales' },
  { value: 'manufacturing', label: 'Manufacturing', icon: <IconTool className="h-5 w-5" />, description: 'Production & Industry' },
  { value: 'startup', label: 'Startup', icon: <IconRocket className="h-5 w-5" />, description: 'Early-stage venture' },
  { value: 'other', label: 'Other', icon: <IconDots className="h-5 w-5" />, description: 'Something else' },
]

const USER_ROLES = [
  { value: 'developer', label: 'Developer', description: 'Building software' },
  { value: 'designer', label: 'Designer', description: 'Creating experiences' },
  { value: 'manager', label: 'Manager', description: 'Leading teams' },
  { value: 'founder', label: 'Founder', description: 'Running the business' },
  { value: 'analyst', label: 'Analyst', description: 'Working with data' },
  { value: 'other', label: 'Other', description: 'Something else' },
]

const MCP_INTEGRATIONS = [
  { value: 'claude', label: 'Claude Desktop', icon: <IconSparkles className="h-5 w-5" />, description: 'AI assistant for coding & writing' },
  { value: 'chatgpt', label: 'ChatGPT', icon: <IconBrain className="h-5 w-5" />, description: 'OpenAI\'s assistant' },
  { value: 'vscode', label: 'VS Code', icon: <IconCode className="h-5 w-5" />, description: 'Code editor integration' },
  { value: 'cursor', label: 'Cursor', icon: <IconBolt className="h-5 w-5" />, description: 'AI-first code editor' },
  { value: 'api', label: 'Custom Apps', icon: <IconPlug className="h-5 w-5" />, description: 'Your own tools' },
  { value: 'slack', label: 'Chat Apps', icon: <IconMessages className="h-5 w-5" />, description: 'Slack, Discord, etc.' },
]

const USE_CASES = [
  { value: 'automation', label: 'Automation', description: 'Automate repetitive tasks' },
  { value: 'analysis', label: 'Data Analysis', description: 'Analyze and visualize data' },
  { value: 'content', label: 'Content', description: 'Create and edit content' },
  { value: 'development', label: 'Development', description: 'Code generation and review' },
  { value: 'support', label: 'Support', description: 'Customer service' },
  { value: 'other', label: 'Other', description: 'Multiple use cases' },
]

export default function OnboardingPage() {
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()
  const { refreshWorkspaces } = useAuthStore()
  const [slugValid, setSlugValid] = useState(false)

  // Initialize data with defaults
  const [initialData, setInitialData] = useState({
    workspaceName: '',
    workspaceSlug: '',
    displayName: '',
    teamSize: 'solo',
    role: '',
    industry: '',
    mcpIntegrations: [],
    emailNotifications: true,
    marketingEmails: false,
  })

  // Update initial data from user when available
  useEffect(() => {
    if (user) {
      setInitialData(prev => ({
        ...prev,
        workspaceName: user.displayName || user.email?.split('@')[0] || '',
        displayName: user.displayName || user.email?.split('@')[0] || '',
      }))
    }
  }, [user])

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login?redirect=/onboarding')
    }
  }, [authLoading, user, router])

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="animate-pulse">Loading...</div>
      </div>
    )
  }

  // Define wizard steps - consolidated to 4 essential steps
  const steps: WizardStep[] = [
    {
      id: 'workspace',
      title: 'Create your workspace',
      description: 'Let\'s set up your workspace',
      icon: <IconBuildingStore className="h-8 w-8" />,
      content: ({ data, updateData }: any) => (
        <div className="space-y-4">
          <TextInput
            data={data}
            updateData={updateData}
            stepId="workspaceName"
            label="Workspace Name"
            placeholder="e.g., Acme Corp"
            required
            helperText="Choose a name that represents your team or project"
          />
          <SlugInput
            value={data.workspaceSlug || ''}
            onChange={(value) => updateData('workspaceSlug', value)}
            onValidationChange={setSlugValid}
            workspaceId="new"
            workspaceName={data.workspaceName}
          />
        </div>
      ),
      validate: (data: any) => {
        if (!data?.workspaceName || data.workspaceName.trim().length < 2) {
          return 'Please enter a workspace name'
        }
        if (!data?.workspaceSlug || !slugValid) {
          return 'Please enter a valid workspace URL'
        }
        return true
      }
    },
    {
      id: 'profile',
      title: 'Tell us about yourself',
      description: 'This helps us personalize your experience',
      icon: <IconUser className="h-8 w-8" />,
      content: ({ data, updateData }: any) => (
        <div className="space-y-4">
          <TextInput
            data={data}
            updateData={updateData}
            stepId="displayName"
            label="Your Name"
            placeholder="John Doe"
            required
          />
          <div className="space-y-2">
            <label className="text-sm font-medium">Your Role</label>
            <SelectCards
              data={data}
              updateData={updateData}
              stepId="role"
              options={USER_ROLES}
              columns={2}
            />
          </div>
        </div>
      ),
      validate: (data: any) => {
        if (!data?.displayName || data.displayName.trim().length < 2) {
          return 'Please enter your name'
        }
        return true
      }
    },
    {
      id: 'organization',
      title: 'About your organization',
      description: 'Help us understand your needs',
      icon: <IconBriefcase className="h-8 w-8" />,
      content: ({ data, updateData }: any) => (
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Team Size</label>
            <SelectCards
              data={data}
              updateData={updateData}
              stepId="teamSize"
              options={TEAM_SIZES}
              columns={2}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Industry</label>
            <SelectCards
              data={data}
              updateData={updateData}
              stepId="industry"
              options={INDUSTRIES}
              columns={2}
            />
          </div>
        </div>
      ),
      validate: (data: any) => {
        if (!data?.teamSize) {
          return 'Please select your team size'
        }
        if (!data?.industry) {
          return 'Please select your industry'
        }
        return true
      }
    },
    {
      id: 'integrations',
      title: 'How will you use MCP?',
      description: 'Select all that apply (optional)',
      icon: <IconPlug className="h-8 w-8" />,
      content: ({ data, updateData }: any) => (
        <div className="space-y-4">
          <SelectCards
            data={data}
            updateData={updateData}
            stepId="mcpIntegrations"
            options={MCP_INTEGRATIONS}
            columns={2}
            multiple
          />
          <p className="text-xs text-muted-foreground text-center">
            You can skip this and set it up later
          </p>
        </div>
      ),
      optional: true,
      skipLabel: 'Skip for now'
    }
  ]

  const createWorkspace = useCreateWorkspace()

  const handleComplete = async (data: any) => {
    try {
      // Create workspace using new hook
      const newWorkspace = await createWorkspace.mutateAsync({
        name: data.workspaceName,
        slug: data.workspaceSlug,
        description: data.workspaceDescription,
        type: 'personal',
        size: data.teamSize,
        industry: data.industry,
        settings: {
          industry: data.industry,
          size: data.teamSize,
          mcpIntegrations: data.mcpIntegrations || [],
          primaryUseCase: data.primaryUseCase,
          needs_onboarding: false,
          onboarding_completed: true,
          onboarding_completed_at: new Date().toISOString(),
        },
      })

      if (!newWorkspace) {
        throw new Error('Failed to create workspace')
      }

      const workspaceId = newWorkspace.id || newWorkspace._id

      // Update user preferences
      await protoboxClient.updateUserPreferences({
        displayName: data.displayName,
        role: data.role,
        emailNotifications: data.emailNotifications !== false,
        marketingEmails: data.marketingEmails === true,
        onboardingCompleted: true,
      })

      // Update last workspace
      await protoboxClient.updateLastWorkspace(workspaceId)

      toast.success('Welcome to your new workspace!')
      await refreshWorkspaces()
      router.push('/dashboard')
    } catch (error) {
      toast.error('Failed to create workspace. Please try again.')
      throw error
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <OnboardingWizard
        steps={steps}
        onComplete={handleComplete}
        initialData={initialData}
        showProgress={true}
        completingText="Creating your workspace..."
        completeText="Get Started"
      />
    </div>
  )
}