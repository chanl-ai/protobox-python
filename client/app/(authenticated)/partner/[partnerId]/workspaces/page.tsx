"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/ui/page-header"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { 
  Plus, 
  Search, 
  MoreHorizontal,
  Building2,
  Users,
  Activity,
  Settings
} from "lucide-react"

// Dummy data
const mockWorkspaces = [
  {
    id: "ws_1",
    name: "Acme Corp Production",
    tenantId: "tenant_acme_001",
    status: "active",
    integrations: 12,
    lastActivity: "2 hours ago",
    requests: 1250,
    owner: "john@acme.com",
    created: "2024-01-15"
  },
  {
    id: "ws_2", 
    name: "StartupXYZ Development",
    tenantId: "tenant_xyz_dev",
    status: "active",
    integrations: 8,
    lastActivity: "5 minutes ago",
    requests: 892,
    owner: "dev@startupxyz.com",
    created: "2024-02-20"
  },
  {
    id: "ws_3",
    name: "BigCorp Testing",
    tenantId: "tenant_bigcorp_test",
    status: "paused",
    integrations: 15,
    lastActivity: "1 day ago", 
    requests: 3421,
    owner: "testing@bigcorp.com",
    created: "2024-01-08"
  },
  {
    id: "ws_4",
    name: "TechFlow Staging",
    tenantId: "tenant_techflow_stg",
    status: "active",
    integrations: 6,
    lastActivity: "30 minutes ago",
    requests: 445,
    owner: "staging@techflow.io",
    created: "2024-03-10"
  },
  {
    id: "ws_5",
    name: "DataCorp Analytics",
    tenantId: "tenant_datacorp_analytics",
    status: "inactive",
    integrations: 22,
    lastActivity: "1 week ago",
    requests: 5678,
    owner: "analytics@datacorp.com",
    created: "2023-12-05"
  }
]

interface WorkspacesPageProps {
  params: { partnerId: string }
}

export default function WorkspacesPage({ params }: WorkspacesPageProps) {
  const [searchQuery, setSearchQuery] = useState("")

  const filteredWorkspaces = mockWorkspaces.filter(workspace =>
    workspace.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    workspace.tenantId.toLowerCase().includes(searchQuery.toLowerCase()) ||
    workspace.owner.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-100 text-green-800">Active</Badge>
      case "paused":
        return <Badge className="bg-yellow-100 text-yellow-800">Paused</Badge>
      case "inactive":
        return <Badge className="bg-gray-100 text-gray-800">Inactive</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const actions = [
    <Button key="create">
      <Plus className="w-4 h-4 mr-2" />
      Create Workspace
    </Button>
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Workspaces"
        subtitle="Manage customer workspaces and monitor their integration usage"
        actions={actions}
      />

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Workspaces</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockWorkspaces.length}</div>
            <p className="text-xs text-muted-foreground">
              {mockWorkspaces.filter(w => w.status === "active").length} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Integrations</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {mockWorkspaces.reduce((sum, w) => sum + w.integrations, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Across all workspaces
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Requests</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {mockWorkspaces.reduce((sum, w) => sum + w.requests, 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+15.3%</span> from last month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Workspace Management</CardTitle>
          <CardDescription>
            Monitor and manage all customer workspaces
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search workspaces, tenant IDs, or owners..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Workspace</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Integrations</TableHead>
                <TableHead>Last Activity</TableHead>
                <TableHead>Monthly Requests</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredWorkspaces.map((workspace) => (
                <TableRow key={workspace.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{workspace.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {workspace.tenantId}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(workspace.status)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {workspace.integrations} integrations
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {workspace.lastActivity}
                  </TableCell>
                  <TableCell>
                    <div className="font-medium">
                      {workspace.requests.toLocaleString()}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm">
                    {workspace.owner}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuItem>
                          <Activity className="mr-2 h-4 w-4" />
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Settings className="mr-2 h-4 w-4" />
                          Configure
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-red-600">
                          Pause Workspace
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {filteredWorkspaces.length === 0 && (
            <div className="text-center py-8">
              <Building2 className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No workspaces found</h3>
              <p className="mt-1 text-sm text-gray-500">
                Try adjusting your search criteria.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}