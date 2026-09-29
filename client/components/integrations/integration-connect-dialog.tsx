"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, CheckCircle2, XCircle, Info, Key, Settings, Puzzle } from "lucide-react";
import { toast } from "sonner";
import { IntegrationWithStatus } from "@/types/integration";

interface IntegrationConnectDialogProps {
  integration: IntegrationWithStatus;
  isOpen: boolean;
  onClose: () => void;
  onConnect: () => void;
  workspaceId: string;
}

interface ConnectResponse {
  type: "oauth2" | "api_key";
  authorization_url?: string;
  display_name?: string;
  instructions?: string[];
  fields?: Array<{
    name: string;
    type: string;
    label: string;
    required: boolean;
    placeholder?: string;
  }>;
  message?: string;
}

interface Tool {
  template_id: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  action_id?: string;
}

export function IntegrationConnectDialog({
  integration,
  isOpen,
  onClose,
  onConnect,
  workspaceId,
}: IntegrationConnectDialogProps) {
  const [activeTab, setActiveTab] = useState("credentials");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [connectInfo, setConnectInfo] = useState<ConnectResponse | null>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [tools, setTools] = useState<Tool[]>([]);
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [settingsSchema, setSettingsSchema] = useState<any>(null);

  // Check if all required fields are filled
  const areAllRequiredFieldsFilled = () => {
    if (!connectInfo?.fields) return false;
    
    return connectInfo.fields
      .filter(field => field.required)
      .every(field => credentials[field.name] && credentials[field.name].trim() !== '');
  };

  // Load connection info when dialog opens
  useEffect(() => {
    if (isOpen && !integration.is_connected) {
      loadConnectInfo();
    }
    if (isOpen) {
      loadTools();
      loadSettings();
    }
  }, [isOpen, integration]);

  const loadConnectInfo = async () => {
    try {
      const response = await fetch(
        `/api/workspaces/${workspaceId}/integrations/${integration.integration_type}/connect`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setConnectInfo(data);
        
        // If OAuth2, open the authorization URL
        if (data.type === "oauth2" && data.authorization_url) {
          window.open(data.authorization_url, "_blank", "width=600,height=700");
          // Start polling for connection status
          pollConnectionStatus();
        }
      }
    } catch (error) {
      console.error("Error loading connect info:", error);
      toast.error("Failed to load connection information");
    }
  };

  const loadTools = async () => {
    try {
      const response = await fetch(
        `/api/workspaces/${workspaceId}/integrations/${integration.integration_type}/tools`
      );

      if (response.ok) {
        const data = await response.json();
        setTools(data.available_tools || []);
      }
    } catch (error) {
      console.error("Error loading tools:", error);
    }
  };

  const loadSettings = async () => {
    try {
      const response = await fetch(
        `/api/workspaces/${workspaceId}/integrations/${integration.integration_type}/settings`
      );

      if (response.ok) {
        const data = await response.json();
        setSettingsSchema(data.schema);
        setSettings(data.current || data.defaults || {});
      }
    } catch (error) {
      console.error("Error loading settings:", error);
    }
  };

  const pollConnectionStatus = () => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `/api/workspaces/${workspaceId}/integrations/${integration.integration_type}`
        );

        if (response.ok) {
          const data = await response.json();
          if (data.status === "connected") {
            clearInterval(interval);
            toast.success(`${integration.display_name} connected successfully!`);
            onConnect();
            onClose();
          }
        }
      } catch (error) {
        console.error("Error polling status:", error);
      }
    }, 2000);

    // Stop polling after 2 minutes
    setTimeout(() => clearInterval(interval), 120000);
  };

  const handleSaveCredentials = async () => {
    setIsSaving(true);
    try {
      const response = await fetch(
        `/api/workspaces/${workspaceId}/integrations/${integration.integration_type}/credentials`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(credentials),
        }
      );

      if (response.ok) {
        toast.success(`${integration.display_name} connected successfully!`);
        onConnect();
        setActiveTab("tools");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to save credentials");
      }
    } catch (error) {
      console.error("Error saving credentials:", error);
      toast.error("Failed to save credentials");
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleTool = async (tool: Tool) => {
    const endpoint = tool.enabled ? "disable" : "enable";
    try {
      const response = await fetch(
        `/api/workspaces/${workspaceId}/integrations/${integration.integration_type}/tools/${tool.template_id}/${endpoint}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (response.ok) {
        toast.success(`Tool ${tool.enabled ? "disabled" : "enabled"} successfully`);
        // Reload tools
        loadTools();
      } else {
        const error = await response.json();
        toast.error(error.detail || `Failed to ${endpoint} tool`);
      }
    } catch (error) {
      console.error(`Error ${endpoint} tool:`, error);
      toast.error(`Failed to ${endpoint} tool`);
    }
  };

  const handleSaveSettings = async () => {
    setIsSaving(true);
    try {
      const response = await fetch(
        `/api/workspaces/${workspaceId}/integrations/${integration.integration_type}/settings`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(settings),
        }
      );

      if (response.ok) {
        toast.success("Settings saved successfully");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to save settings");
      }
    } catch (error) {
      console.error("Error saving settings:", error);
      toast.error("Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  const renderCredentialsTab = () => {
    if (integration.is_connected) {
      return (
        <div className="space-y-4">
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              {integration.display_name} is connected and authenticated.
            </AlertDescription>
          </Alert>
          <div className="space-y-2">
            <Label>Connection Status</Label>
            <div className="flex items-center gap-2">
              <Badge variant="default">Connected</Badge>
              {integration.connected_at && (
                <span className="text-sm text-muted-foreground">
                  Since {new Date(integration.connected_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
          <Button
            variant="destructive"
            onClick={() => {
              // Handle disconnect
              toast.info("Disconnect functionality coming soon");
            }}
          >
            Disconnect
          </Button>
        </div>
      );
    }

    if (!connectInfo) {
      return (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      );
    }

    if (connectInfo.type === "api_key") {
      return (
        <div className="space-y-4">
          {connectInfo.instructions && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                <ol className="list-decimal list-inside space-y-1">
                  {connectInfo.instructions.map((instruction, index) => (
                    <li key={index}>{instruction}</li>
                  ))}
                </ol>
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            {connectInfo.fields?.map((field) => (
              <div key={field.name} className="space-y-2">
                <Label htmlFor={field.name}>
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                <Input
                  id={field.name}
                  type={field.type}
                  placeholder={field.placeholder}
                  value={credentials[field.name] || ""}
                  onChange={(e) =>
                    setCredentials({ ...credentials, [field.name]: e.target.value })
                  }
                  required={field.required}
                />
              </div>
            ))}
          </div>

          <Button
            onClick={handleSaveCredentials}
            disabled={isSaving || !areAllRequiredFieldsFilled()}
            className="w-full"
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Validating...
              </>
            ) : (
              "Connect"
            )}
          </Button>
        </div>
      );
    }

    // OAuth2 flow
    return (
      <div className="space-y-4">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            A popup window should have opened for you to authorize {integration.display_name}.
            If it didn't open, click the button below.
          </AlertDescription>
        </Alert>
        <Button
          onClick={() => window.open(connectInfo.authorization_url, "_blank")}
          className="w-full"
        >
          Authorize {integration.display_name}
        </Button>
      </div>
    );
  };

  const renderToolsTab = () => {
    if (!integration.is_connected) {
      return (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Connect {integration.display_name} first to manage tools.
          </AlertDescription>
        </Alert>
      );
    }

    if (tools.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          No tools available for this integration.
        </div>
      );
    }

    return (
      <ScrollArea className="h-[400px] pr-4">
        <div className="space-y-4">
          {tools.map((tool) => (
            <div
              key={tool.template_id}
              className="flex items-start space-x-3 rounded-lg border p-4"
            >
              <Switch
                checked={tool.enabled}
                onCheckedChange={() => handleToggleTool(tool)}
                disabled={!integration.is_connected}
              />
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-medium">{tool.name}</h4>
                  <Badge variant="outline" className="text-xs">
                    {tool.category}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{tool.description}</p>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    );
  };

  const renderSettingsTab = () => {
    if (!settingsSchema || !settingsSchema.properties) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          No advanced settings available for this integration.
        </div>
      );
    }

    return (
      <ScrollArea className="h-[400px] pr-4">
        <div className="space-y-6">
          {Object.entries(settingsSchema.properties).map(([key, schema]: [string, any]) => (
            <div key={key} className="space-y-4">
              <h4 className="font-medium">{schema.title || key}</h4>
              {schema.type === "object" ? (
                <div className="space-y-4 pl-4">
                  {Object.entries(schema.properties || {}).map(([subKey, subSchema]: [string, any]) => (
                    <div key={subKey} className="space-y-2">
                      <Label htmlFor={`${key}.${subKey}`}>
                        {subSchema.title || subKey}
                        {subSchema.description && (
                          <span className="block text-xs text-muted-foreground">
                            {subSchema.description}
                          </span>
                        )}
                      </Label>
                      {renderSettingInput(`${key}.${subKey}`, subSchema, 
                        settings[key]?.[subKey] ?? subSchema.default)}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {schema.description && (
                    <span className="text-xs text-muted-foreground">
                      {schema.description}
                    </span>
                  )}
                  {renderSettingInput(key, schema, settings[key] ?? schema.default)}
                </div>
              )}
            </div>
          ))}
          
          <Button onClick={handleSaveSettings} disabled={isSaving} className="w-full">
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save Settings"
            )}
          </Button>
        </div>
      </ScrollArea>
    );
  };

  const renderSettingInput = (path: string, schema: any, value: any) => {
    const updateSetting = (newValue: any) => {
      const keys = path.split(".");
      if (keys.length === 1) {
        setSettings({ ...settings, [keys[0]]: newValue });
      } else {
        const newSettings = { ...settings };
        let current = newSettings;
        for (let i = 0; i < keys.length - 1; i++) {
          if (!current[keys[i]]) {
            current[keys[i]] = {};
          }
          current = current[keys[i]];
        }
        current[keys[keys.length - 1]] = newValue;
        setSettings(newSettings);
      }
    };

    if (schema.type === "boolean") {
      return (
        <Switch
          checked={value || false}
          onCheckedChange={updateSetting}
        />
      );
    }

    if (schema.enum) {
      return (
        <select
          className="w-full rounded-md border border-input bg-background px-3 py-2"
          value={value || ""}
          onChange={(e) => updateSetting(e.target.value)}
        >
          <option value="">Select...</option>
          {schema.enum.map((option: string) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    if (schema.type === "integer" || schema.type === "number") {
      return (
        <Input
          type="number"
          value={value || ""}
          onChange={(e) => updateSetting(
            schema.type === "integer" ? parseInt(e.target.value) : parseFloat(e.target.value)
          )}
          min={schema.minimum}
          max={schema.maximum}
        />
      );
    }

    return (
      <Input
        type="text"
        value={value || ""}
        onChange={(e) => updateSetting(e.target.value)}
        placeholder={schema.examples?.[0] || ""}
      />
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <img
              src={integration.icon_url || "/integrations/default.png"}
              alt={integration.display_name}
              className="h-6 w-6"
            />
            {integration.display_name} Settings
          </DialogTitle>
          <DialogDescription>
            Configure {integration.display_name} connection, tools, and settings
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="credentials" className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              Credentials
            </TabsTrigger>
            <TabsTrigger value="tools" className="flex items-center gap-2">
              <Puzzle className="h-4 w-4" />
              Tools
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Advanced
            </TabsTrigger>
          </TabsList>

          <TabsContent value="credentials" className="mt-4">
            {renderCredentialsTab()}
          </TabsContent>

          <TabsContent value="tools" className="mt-4">
            {renderToolsTab()}
          </TabsContent>

          <TabsContent value="settings" className="mt-4">
            {renderSettingsTab()}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}