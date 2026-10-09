"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import {
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Trash2,
  Mail,
  Users,
} from "lucide-react"
import { useState, useEffect } from "react"
import { protoboxClient } from "@/lib/api/protobox-client"
import { useWorkspaceReady } from "@/hooks"
import { IntegrationType } from "./integration-card"
import { IntegrationSettings } from "./integration-settings"
import { GoogleCalendarIntegrationSettings } from "./google-calendar-integration-settings"

interface IntegrationSettingsDialogProps {
  integration: IntegrationType | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave?: (settings: any) => void
  onDisconnect?: () => void
  onTestConnection?: () => Promise<boolean>
  onRefreshToken?: () => Promise<void>
}

export function IntegrationSettingsDialog({
  integration,
  open,
  onOpenChange,
  onSave,
  onDisconnect,
  onTestConnection,
  onRefreshToken,
}: IntegrationSettingsDialogProps) {
  const { workspaceId } = useWorkspaceReady()
  const [isLoading, setIsLoading] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
  } | null>(null)
  const [integrationData, setIntegrationData] = useState<any>(null)
  
  // Advanced settings state
  const [advancedSettings, setAdvancedSettings] = useState({
    // Google Calendar specific
    defaultCalendar: "primary",
    timezone: "America/New_York",
    workingHoursStart: "09:00",
    workingHoursEnd: "17:00",
    bufferTime: "15",
    defaultDuration: "30",
    autoDeclineConflicts: false,
    weekendsAvailable: false,
    defaultLocation: "",
    defaultVisibility: "default",
    defaultReminder: "10",
    defaultReminderMethod: "popup",
    showDeclinedEvents: false,
    colorCoding: true,
    
    // Gmail specific
    emailSignature: "",
    defaultLabel: "inbox",
    vacationResponder: false,
    
    // GitHub specific
    defaultRepo: "",
    defaultBranch: "main",
    autoMerge: false,
  })

  // Fetch integration-specific data when dialog opens
  useEffect(() => {
    if (open && integration && workspaceId && integration.status === "connected") {
      // Fetch integration data for advanced settings
      protoboxClient.getIntegrationData(workspaceId, integration.id)
        .then(response => {
          if (response.data && !response.data.error) {
            setIntegrationData(response.data)
          }
        })
        .catch(error => {
          console.error("Failed to fetch integration data:", error)
        })
    }
  }, [open, integration, workspaceId])

  if (!integration) return null

  const handleTestConnection = async () => {
    setIsLoading(true)
    setTestResult(null)
    try {
      const success = await onTestConnection?.()
      setTestResult({
        success: success ?? false,
        message: success
          ? "Connection test successful!"
          : "Connection test failed. Please check your credentials.",
      })
    } catch (error) {
      setTestResult({
        success: false,
        message: "Connection test failed: " + (error as Error).message,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleRefreshToken = async () => {
    setIsLoading(true)
    try {
      await onRefreshToken?.()
      setTestResult({
        success: true,
        message: "Token refreshed successfully!",
      })
    } catch (error) {
      setTestResult({
        success: false,
        message: "Failed to refresh token: " + (error as Error).message,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDisconnect = () => {
    onDisconnect?.()
    onOpenChange(false)
  }

  const handleSave = () => {
    onSave?.({ settings: advancedSettings })
    onOpenChange(false)
  }

  const handleSettingsChange = (settings: any) => {
    // Handle any settings changes from the IntegrationSettings component
    console.log('Settings changed:', settings)
  }

  const renderAdvancedSettings = () => {
    switch (integration.id) {
      case "google_calendar":
        return (
          <GoogleCalendarIntegrationSettings
            settings={advancedSettings}
            onChange={(patch) =>
              setAdvancedSettings((prev) => ({ ...prev, ...patch }))
            }
            integrationData={integrationData}
          />
        )

      case "gmail":
        return (
          <>
            <div className="space-y-4">
              <h3 className="text-sm font-medium flex items-center gap-2">
                <Mail className="h-4 w-4" />
                Email Preferences
              </h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="defaultLabel">Default Label</Label>
                  <Select
                    value={advancedSettings.defaultLabel}
                    onValueChange={(value) => setAdvancedSettings({ ...advancedSettings, defaultLabel: value })}
                  >
                    <SelectTrigger id="defaultLabel">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {integrationData?.labels ? (
                        integrationData.labels.map((label: any) => (
                          <SelectItem key={label.id} value={label.id}>
                            {label.name}
                          </SelectItem>
                        ))
                      ) : (
                        <>
                          <SelectItem value="INBOX">Inbox</SelectItem>
                          <SelectItem value="SENT">Sent</SelectItem>
                          <SelectItem value="DRAFT">Drafts</SelectItem>
                          <SelectItem value="IMPORTANT">Important</SelectItem>
                        </>
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="emailSignature">Email Signature</Label>
                  <Input
                    id="emailSignature"
                    placeholder="Your default signature"
                    value={advancedSettings.emailSignature}
                    onChange={(e) => setAdvancedSettings({ ...advancedSettings, emailSignature: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="vacation">Vacation Responder</Label>
                  <p className="text-sm text-muted-foreground">Auto-reply when away</p>
                </div>
                <Switch
                  id="vacation"
                  checked={advancedSettings.vacationResponder}
                  onCheckedChange={(checked) => setAdvancedSettings({ ...advancedSettings, vacationResponder: checked })}
                />
              </div>
            </div>
          </>
        )

      case "github":
        return (
          <>
            <div className="space-y-4">
              <h3 className="text-sm font-medium flex items-center gap-2">
                <Users className="h-4 w-4" />
                Repository Settings
              </h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="defaultRepo">Default Repository</Label>
                  <Select
                    value={advancedSettings.defaultRepo}
                    onValueChange={(value) => setAdvancedSettings({ ...advancedSettings, defaultRepo: value })}
                  >
                    <SelectTrigger id="defaultRepo">
                      <SelectValue placeholder="Select repository" />
                    </SelectTrigger>
                    <SelectContent>
                      {integrationData?.repositories ? (
                        integrationData.repositories.map((repo: any) => (
                          <SelectItem key={repo.id} value={repo.full_name}>
                            {repo.full_name}
                          </SelectItem>
                        ))
                      ) : (
                        <SelectItem value="">No repositories found</SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="defaultBranch">Default Branch</Label>
                  <Input
                    id="defaultBranch"
                    value={advancedSettings.defaultBranch}
                    onChange={(e) => setAdvancedSettings({ ...advancedSettings, defaultBranch: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="autoMerge">Auto-merge PRs</Label>
                  <p className="text-sm text-muted-foreground">Automatically merge when checks pass</p>
                </div>
                <Switch
                  id="autoMerge"
                  checked={advancedSettings.autoMerge}
                  onCheckedChange={(checked) => setAdvancedSettings({ ...advancedSettings, autoMerge: checked })}
                />
              </div>
            </div>
          </>
        )

      default:
        return null
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl overflow-y-auto max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold flex items-center gap-2">
            {integration.name} Integration
            <Badge
              variant={integration.status === "connected" ? "default" : "secondary"}
              className="gap-1 ml-2"
            >
              {integration.status === "connected" ? (
                <>
                  <CheckCircle2 className="h-3 w-3" />
                  Connected
                </>
              ) : (
                <>
                  <AlertCircle className="h-3 w-3" />
                  Not Connected
                </>
              )}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Configure MCP tools and advanced settings for {integration.name}
          </DialogDescription>
        </DialogHeader>

        {testResult && (
          <div
            className={cn(
              "rounded-lg p-3 text-sm",
              testResult.success
                ? "bg-green-50 text-green-800 border border-green-200"
                : "bg-red-50 text-red-800 border border-red-200"
            )}
          >
            {testResult.message}
          </div>
        )}

        <IntegrationSettings
          integrationId={integration.id}
          integrationName={integration.name}
          isConnected={integration.status === "connected"}
          onSettingsChange={handleSettingsChange}
          className="mt-6"
        >
          {renderAdvancedSettings()}
        </IntegrationSettings>

        <DialogFooter className="mt-6 flex-col sm:flex-row gap-2">
          <div className="flex gap-2 flex-1">
            {integration.status === "connected" && (
              <>
                <Button
                  variant="outline"
                  onClick={handleTestConnection}
                  disabled={isLoading}
                >
                  <RefreshCw className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")} />
                  Test
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="destructive"
                      disabled={isLoading}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Disconnect
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Disconnect {integration.name}?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will disconnect your {integration.name} integration and disable all MCP tools for this service. 
                        You'll need to reconnect and reconfigure your settings to use {integration.name} again.
                        <br /><br />
                        This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction 
                        onClick={handleDisconnect}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        Disconnect
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave}>
              Save Changes
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}