"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Globe,
  ExternalLink,
} from "lucide-react"
import type { ImportPreviewResponse, ActionPreview } from "../../lib/api/actions-import"

interface ActionsPreviewProps {
  preview: ImportPreviewResponse
  selectedActions: Set<string>
  onToggleAction: (actionName: string) => void
  onSelectAll: () => void
  onDeselectAll: () => void
}

export function ActionsPreview({
  preview,
  selectedActions,
  onToggleAction,
  onSelectAll,
  onDeselectAll,
}: ActionsPreviewProps) {
  const getMethodColor = (method: string) => {
    switch (method.toUpperCase()) {
      case "GET": return "bg-green-100 text-green-800 border-green-200"
      case "POST": return "bg-blue-100 text-blue-800 border-blue-200"
      case "PUT": return "bg-orange-100 text-orange-800 border-orange-200"
      case "DELETE": return "bg-red-100 text-red-800 border-red-200"
      case "PATCH": return "bg-purple-100 text-purple-800 border-purple-200"
      default: return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  return (
    <div className="space-y-4 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h3 className="text-lg font-semibold">
              {preview.actions_count} Action{preview.actions_count !== 1 ? 's' : ''} Found
            </h3>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onSelectAll}
                disabled={selectedActions.size === preview.previews.length}
              >
                Select All
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onDeselectAll}
                disabled={selectedActions.size === 0}
              >
                Deselect All
              </Button>
            </div>
          </div>
          <Badge variant="secondary">
            {selectedActions.size} selected
          </Badge>
        </div>

        <div className="space-y-3">
          {preview.previews.map((action: ActionPreview, index: number) => {
            const isSelected = selectedActions.has(action.name)
            return (
              <Card
                key={index}
                className={`cursor-pointer transition-colors ${
                  isSelected ? "border-primary bg-primary/5" : "hover:bg-muted/50"
                }`}
                onClick={() => onToggleAction(action.name)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => onToggleAction(action.name)}
                      />
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={`text-xs font-mono ${getMethodColor(action.method)}`}
                        >
                          {action.method}
                        </Badge>
                        <Globe className="w-4 h-4 text-muted-foreground" />
                      </div>
                    </div>
                  </div>
                  <div className="ml-9">
                    <CardTitle className="text-base">{action.name}</CardTitle>
                    {action.description && (
                      <CardDescription className="mt-1">
                        {action.description}
                      </CardDescription>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="ml-9 space-y-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <ExternalLink className="w-3 h-3" />
                      <code className="text-xs bg-muted px-1 py-0.5 rounded">
                        {action.url}
                      </code>
                    </div>
                    {action.variables.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-muted-foreground">Parameters:</div>
                        <div className="flex flex-wrap gap-1">
                          {action.variables.map((variable: any, vIndex: number) => (
                            <Badge
                              key={vIndex}
                              variant={variable.required ? "default" : "secondary"}
                              className="text-xs"
                              title={`${variable.description}${variable.example ? ` (example: ${variable.example})` : ''}`}
                            >
                              {variable.in && variable.in !== 'body' && (
                                <span className="opacity-60 mr-1">{variable.in}:</span>
                              )}
                              {variable.name}
                              <span className="ml-1 opacity-70">({variable.type})</span>
                              {variable.example && (
                                <span className="ml-1 opacity-50 text-xs">={String(variable.example)}</span>
                              )}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Tags */}
                    {action.tags && action.tags.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs font-medium text-muted-foreground">Tags:</div>
                        <div className="flex flex-wrap gap-1">
                          {action.tags.map((tag: string, tagIndex: number) => (
                            <Badge key={tagIndex} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Security Schemes */}
                    {action.security_schemes && action.security_schemes.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs font-medium text-muted-foreground">Authentication:</div>
                        <div className="flex flex-wrap gap-1">
                          {action.security_schemes.map((scheme: string, schemeIndex: number) => (
                            <Badge key={schemeIndex} variant="secondary" className="text-xs">
                              🔐 {scheme}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Request Example */}
                    {action.request_example && (
                      <details className="space-y-1">
                        <summary className="text-xs font-medium text-muted-foreground cursor-pointer hover:text-foreground">
                          Request Example
                        </summary>
                        <div className="ml-4 space-y-1">
                          <div className="text-xs text-muted-foreground">
                            Content-Type: {action.request_example.content_type}
                          </div>
                          <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                            {JSON.stringify(action.request_example.body, null, 2)}
                          </pre>
                        </div>
                      </details>
                    )}

                    {/* Response Examples */}
                    {action.response_examples && Object.keys(action.response_examples).length > 0 && (
                      <details className="space-y-1">
                        <summary className="text-xs font-medium text-muted-foreground cursor-pointer hover:text-foreground">
                          Response Examples
                        </summary>
                        <div className="ml-4 space-y-2">
                          {Object.entries(action.response_examples).map(([statusCode, response]) => (
                            <div key={statusCode} className="space-y-1">
                              <div className="flex items-center gap-2">
                                <Badge 
                                  variant={statusCode.startsWith('2') ? 'default' : 'destructive'} 
                                  className="text-xs"
                                >
                                  {statusCode}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  {response.description}
                                </span>
                              </div>
                              <div className="text-xs text-muted-foreground ml-2">
                                Content-Type: {response.content_type}
                              </div>
                              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto ml-2">
                                {JSON.stringify(response.body, null, 2)}
                              </pre>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
    </div>
  )
}
