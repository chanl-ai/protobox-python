"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  FileText,
  Terminal,
  Globe,
  Download,
  Zap,
} from "lucide-react"


export type ImportType = "openapi" | "curl"

interface SourceSelectionProps {
  importType: ImportType | ""
  setImportType: (type: ImportType) => void
}

export function SourceSelection({
  importType,
  setImportType,
}: SourceSelectionProps) {
  return (
    <div className="space-y-6 p-4">
        {/* Source Selection Cards */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Card 
            className={`cursor-pointer transition-all hover:shadow-sm ${
              importType === "openapi" 
                ? "border-primary border-2" 
                : "border-border hover:border-muted-foreground/50"
            }`}
            onClick={() => setImportType("openapi")}
          >
            <CardHeader className="pb-3">
              <FileText className="h-5 w-5 text-muted-foreground mb-2" />
              <CardTitle className="text-base">OpenAPI Specification</CardTitle>
              <CardDescription className="text-sm">
                Import from OpenAPI/Swagger specs
              </CardDescription>
            </CardHeader>
          </Card>

          <Card 
            className={`cursor-pointer transition-all hover:shadow-sm ${
              importType === "curl" 
                ? "border-primary border-2" 
                : "border-border hover:border-muted-foreground/50"
            }`}
            onClick={() => setImportType("curl")}
          >
            <CardHeader className="pb-3">
              <Terminal className="h-5 w-5 text-muted-foreground mb-2" />
              <CardTitle className="text-base">cURL Command</CardTitle>
              <CardDescription className="text-sm">
                Quick import from single endpoints
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="opacity-50 cursor-not-allowed">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between mb-2">
                <Globe className="h-5 w-5 text-muted-foreground" />
                <Badge variant="secondary" className="text-xs">
                  Soon
                </Badge>
              </div>
              <CardTitle className="text-base">Postman Collection</CardTitle>
              <CardDescription className="text-sm">
                Import from Postman exports
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="opacity-50 cursor-not-allowed">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between mb-2">
                <Download className="h-5 w-5 text-muted-foreground" />
                <Badge variant="secondary" className="text-xs">
                  Soon
                </Badge>
              </div>
              <CardTitle className="text-base">Insomnia Export</CardTitle>
              <CardDescription className="text-sm">
                Import from Insomnia REST client
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="opacity-50 cursor-not-allowed">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between mb-2">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <Badge variant="secondary" className="text-xs">
                  Soon
                </Badge>
              </div>
              <CardTitle className="text-base">HAR File</CardTitle>
              <CardDescription className="text-sm">
                Import from browser recordings
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="opacity-50 cursor-not-allowed">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between mb-2">
                <Zap className="h-5 w-5 text-muted-foreground" />
                <Badge variant="secondary" className="text-xs">
                  Soon
                </Badge>
              </div>
              <CardTitle className="text-base">GraphQL Schema</CardTitle>
              <CardDescription className="text-sm">
                Import GraphQL queries/mutations
              </CardDescription>
            </CardHeader>
          </Card>
        </div>




    </div>
  )
}
