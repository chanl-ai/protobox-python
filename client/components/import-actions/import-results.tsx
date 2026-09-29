"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  CheckCircle,
  XCircle,
  ExternalLink,
} from "lucide-react"
import type { ImportResult } from "../../lib/api/actions-import"

interface ImportResultsProps {
  importResult: ImportResult
}

export function ImportResults({ importResult }: ImportResultsProps) {
  return (
    <div className="space-y-6 p-4">
        <div className="text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold">Import Completed</h3>
          <p className="text-muted-foreground">
            {importResult.summary.created} action{importResult.summary.created !== 1 ? 's' : ''} created successfully
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Parsed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{importResult.summary.parsed}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-green-600">
                Created
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {importResult.summary.created}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-orange-600">
                Skipped
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {importResult.summary.skipped}
              </div>
            </CardContent>
          </Card>
        </div>

        {importResult.created.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Created Actions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {importResult.created.map((actionId: string, index: number) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-green-50 rounded">
                    <span className="text-sm font-medium">Action {index + 1}</span>
                    <Button variant="ghost" size="sm" className="h-6 text-xs">
                      <ExternalLink className="w-3 h-3 mr-1" />
                      View
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {importResult.skipped.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <XCircle className="w-4 h-4 text-orange-500" />
                Skipped Actions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {importResult.skipped.map((skipped: any, index: number) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-orange-50 rounded">
                    <span className="text-sm font-medium">{skipped.name}</span>
                    <Badge variant="outline" className="text-xs">
                      {skipped.reason}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
    </div>
  )
}
