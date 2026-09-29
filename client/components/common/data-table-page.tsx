"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DataTable } from "./data-table"
import { Eye, EyeOff } from "lucide-react"
import { cn } from "@/lib/utils"

interface Stat {
  title: string
  value: string
  description?: string
  icon?: React.ComponentType<{ className?: string }>
}

interface DataTablePageProps<TData> {
  // Page configuration
  pageTitle: string
  pageDescription?: string
  pageIcon?: React.ComponentType<{ className?: string }>
  
  // Stats configuration
  stats?: Stat[]
  statsColumns?: 2 | 3 | 4
  localStorageKey?: string // Key for storing analytics visibility preference
  
  // Table configuration
  tableTitle: string
  tableDescription?: string
  columns: any[]
  data: TData[]
  toolbar?: React.ComponentType<{ table: any }>
  
  // Actions
  headerActions?: React.ReactNode
  
  // Additional content
  children?: React.ReactNode
}

export function DataTablePage<TData>({
  pageTitle,
  pageDescription,
  pageIcon: PageIcon,
  stats,
  statsColumns = 3,
  localStorageKey,
  tableTitle,
  tableDescription,
  columns,
  data,
  toolbar,
  headerActions,
  children,
}: DataTablePageProps<TData>) {
  const [showAnalytics, setShowAnalytics] = useState(true)

  // Load analytics visibility preference from localStorage
  useEffect(() => {
    if (localStorageKey) {
      const stored = localStorage.getItem(localStorageKey)
      if (stored !== null) {
        setShowAnalytics(stored === 'true')
      }
    }
  }, [localStorageKey])

  // Save analytics visibility preference to localStorage
  const toggleAnalytics = () => {
    const newValue = !showAnalytics
    setShowAnalytics(newValue)
    if (localStorageKey) {
      localStorage.setItem(localStorageKey, String(newValue))
    }
  }

  const gridColsClass = {
    2: "md:grid-cols-2",
    3: "md:grid-cols-3",
    4: "md:grid-cols-2 lg:grid-cols-4",
  }[statsColumns]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          {PageIcon && <PageIcon className="h-8 w-8 text-muted-foreground" />}
          <div>
            <h1 className="text-3xl font-bold">{pageTitle}</h1>
            {pageDescription && (
              <p className="text-muted-foreground">{pageDescription}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Analytics Toggle Button */}
          {stats && stats.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={toggleAnalytics}
              className="gap-2"
            >
              {showAnalytics ? (
                <>
                  <EyeOff className="h-4 w-4" />
                  Hide Analytics
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4" />
                  Show Analytics
                </>
              )}
            </Button>
          )}
          {headerActions}
        </div>
      </div>

      {/* Stats Cards */}
      {stats && stats.length > 0 && showAnalytics && (
        <div className={cn("grid gap-4", gridColsClass)}>
          {stats.map((stat, index) => (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                {stat.icon && <stat.icon className="h-4 w-4 text-muted-foreground" />}
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                {stat.description && (
                  <p className="text-xs text-muted-foreground">
                    {stat.description}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Data Table */}
      <Card>
        <CardHeader>
          <CardTitle>{tableTitle}</CardTitle>
          {tableDescription && (
            <CardDescription>{tableDescription}</CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={data} toolbar={toolbar} />
        </CardContent>
      </Card>

      {/* Additional content (dialogs, etc.) */}
      {children}
    </div>
  )
}