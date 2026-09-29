"use client"

import { useState, useEffect } from "react"
import { Copy, Check, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"
import { mcpOAuthApi, type MCPOAuthClient } from "@/lib/api/mcp-oauth"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { CreateOAuthClientDialog } from "./create-oauth-client-dialog"

interface OAuthClientsTabProps {
  workspaceId: string
}

export function OAuthClientsTab({ workspaceId }: OAuthClientsTabProps) {
  const { toast } = useToast()
  const [clients, setClients] = useState<MCPOAuthClient[]>([])
  const [loading, setLoading] = useState(false)
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  // WorkspaceLoadingGuard guarantees workspaceId is valid
  useEffect(() => {
    loadClients()
  }, [workspaceId])

  const loadClients = async () => {
    
    setLoading(true)
    try {
      const data = await mcpOAuthApi.listClients(workspaceId)
      setClients(data)
    } catch (error) {
      toast({
        title: "Error loading OAuth clients",
        description: error instanceof Error ? error.message : "Failed to load OAuth clients",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteClient = async (clientId: string) => {
    try {
      await mcpOAuthApi.revokeClient(workspaceId, clientId)
      await loadClients()
      toast({
        title: "Client revoked",
        description: "The OAuth client has been revoked",
      })
    } catch (error) {
      toast({
        title: "Error revoking client",
        description: error instanceof Error ? error.message : "Failed to revoke client",
        variant: "destructive",
      })
    }
  }

  const copyToClipboard = async (text: string, itemId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItem(itemId)
      setTimeout(() => setCopiedItem(null), 2000)
      toast({
        title: "Copied",
        description: "Copied to clipboard",
      })
    } catch {
      toast({
        title: "Failed to copy",
        description: "Please copy manually",
        variant: "destructive",
      })
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  // Pagination calculations
  const totalPages = Math.ceil(clients.length / itemsPerPage)
  const paginatedClients = clients.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  // No need for workspace loading checks - guaranteed by layout guard

  if (loading && clients.length === 0) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-semibold">OAuth 2.1 Clients</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Connect AI assistants like Claude, ChatGPT, and Cursor to your MCP server using OAuth 2.1.
          </p>
        </div>
        <CreateOAuthClientDialog
          workspaceId={workspaceId}
          onSuccess={loadClients}
        />
      </div>

      {/* Clients List */}
      {clients.length === 0 ? (
        <div className="text-center py-12 border rounded-lg">
          <div className="mx-auto h-12 w-12 text-muted-foreground opacity-50">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
            </svg>
          </div>
          <h4 className="mt-4 text-sm font-semibold">No OAuth clients yet</h4>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your first OAuth client to connect AI assistants
          </p>
        </div>
      ) : (
        <>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[200px]">Name</TableHead>
                  <TableHead className="w-[150px]">Client ID</TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                  <TableHead className="w-[100px]">Created</TableHead>
                  <TableHead className="w-[100px]">Last Used</TableHead>
                  <TableHead>Scopes</TableHead>
                  <TableHead className="w-[100px] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedClients.map((client) => (
                  <TableRow key={client.client_id}>
                    <TableCell className="font-medium">
                      <div>
                        <p>{client.client_name}</p>
                        {client.description && (
                          <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                            {client.description}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <code className="text-xs truncate block max-w-[120px]">
                          {client.client_id}
                        </code>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0"
                          onClick={() => copyToClipboard(client.client_id, client.client_id)}
                        >
                          {copiedItem === client.client_id ? (
                            <Check className="h-3 w-3 text-green-600" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={client.status === "active" ? "default" : "destructive"} className="text-xs">
                        {client.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatDate(client.created_at)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {client.last_used_at ? formatDate(client.last_used_at) : "Never"}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {client.allowed_scopes.slice(0, 2).map(scope => (
                          <Badge key={scope} variant="outline" className="text-xs">
                            {scope.replace('mcp:', '')}
                          </Badge>
                        ))}
                        {client.allowed_scopes.length > 2 && (
                          <Badge variant="outline" className="text-xs">
                            +{client.allowed_scopes.length - 2}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteClient(client.client_id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, clients.length)} of {clients.length} clients
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}