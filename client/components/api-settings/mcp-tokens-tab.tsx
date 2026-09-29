"use client"

import { useState, useEffect } from "react"
import { Trash2, Key } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"
import { mcpTokensApi, type MCPToken } from "@/lib/api/mcp-tokens"
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
import { CreateMCPTokenDialog } from "./create-mcp-token-dialog"

interface MCPTokensTabProps {
  workspaceId: string
}

export function MCPTokensTab({ workspaceId }: MCPTokensTabProps) {
  const { toast } = useToast()
  const [tokens, setTokens] = useState<MCPToken[]>([])
  const [loading, setLoading] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  useEffect(() => {
    if (workspaceId) {
      loadTokens()
    }
  }, [workspaceId])

  const loadTokens = async () => {
    setLoading(true)
    try {
      const data = await mcpTokensApi.list(workspaceId)
      setTokens(data)
    } catch (error) {
      toast({
        title: "Error loading tokens",
        description: error instanceof Error ? error.message : "Failed to load MCP tokens",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteToken = async (tokenId: string, tokenName: string) => {
    // Protect internal assistant token
    if (tokenName === "internal-assistant-mcp") {
      toast({
        title: "Protected token",
        description: "The internal assistant token cannot be deleted as it may impact chat functionality. You can regenerate it instead.",
        variant: "destructive",
      })
      return
    }
    
    try {
      await mcpTokensApi.revoke(workspaceId, tokenId)
      await loadTokens()
      toast({
        title: "Token deleted",
        description: "The MCP token has been deleted",
      })
    } catch (error) {
      toast({
        title: "Error deleting token",
        description: error instanceof Error ? error.message : "Failed to delete token",
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
  const totalPages = Math.ceil(tokens.length / itemsPerPage)
  const paginatedTokens = tokens.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  // No need for workspace loading checks - guaranteed by layout guard

  if (loading && tokens.length === 0) {
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
          <h3 className="text-lg font-semibold">MCP Server Tokens</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Direct tokens for connecting AI assistants like Claude and ChatGPT to your MCP server.
          </p>
        </div>
        <CreateMCPTokenDialog workspaceId={workspaceId} onSuccess={loadTokens} />
      </div>

      {/* Tokens List */}
      {tokens.length === 0 ? (
        <div className="text-center py-12 border rounded-lg">
          <Key className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
          <h4 className="mt-4 text-sm font-semibold">No tokens yet</h4>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your first MCP token to get started
          </p>
        </div>
      ) : (
        <>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[200px]">Name</TableHead>
                  <TableHead className="w-[150px]">Token ID</TableHead>
                  <TableHead className="w-[100px]">Created</TableHead>
                  <TableHead className="w-[100px]">Expires</TableHead>
                  <TableHead className="w-[100px]">Last Used</TableHead>
                  <TableHead className="w-[80px] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedTokens.map((token) => (
                  <TableRow key={token.token_id}>
                    <TableCell className="font-medium">
                      <div>
                        <p className="flex items-center gap-2">
                          {token.name}
                          {token.name === "internal-assistant-mcp" && (
                            <Badge variant="secondary" className="text-xs">Protected</Badge>
                          )}
                        </p>
                        {token.description && (
                          <p className="text-xs text-muted-foreground truncate max-w-[180px]">{token.description}</p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <code className="text-xs truncate block max-w-[140px]">{token.token_id}</code>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm">{formatDate(token.created_at)}</span>
                    </TableCell>
                    <TableCell>
                      {token.expires_at ? (
                        <Badge variant={new Date(token.expires_at) < new Date() ? "destructive" : "secondary"} className="text-xs">
                          {new Date(token.expires_at) < new Date() ? "Expired" : formatDate(token.expires_at)}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          Never
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {token.last_used_at ? formatDate(token.last_used_at) : "Never"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      {token.name === "internal-assistant-mcp" ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled
                          title="Protected token cannot be deleted"
                        >
                          <Trash2 className="h-4 w-4 text-muted-foreground opacity-50" />
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          type="button"
                          onClick={() => handleDeleteToken(token.token_id, token.name)}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      )}
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
                Showing {(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, tokens.length)} of {tokens.length} tokens
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