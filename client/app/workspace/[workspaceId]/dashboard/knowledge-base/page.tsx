import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Upload, FileText, Search, Download, Trash2, Eye, Plus, RefreshCw, Database, Brain, MessageSquare, BookOpen } from "lucide-react"

export default function KnowledgeBasePage() {
  const documents = [
    { 
      id: "doc_1", 
      name: "API Documentation.pdf", 
      type: "PDF", 
      size: "2.3 MB", 
      status: "processed", 
      chunks: 47, 
      questions: 23,
      uploadedAt: "2024-01-15",
      lastQueried: "2 minutes ago"
    },
    { 
      id: "doc_2", 
      name: "Product Manual.docx", 
      type: "DOCX", 
      size: "1.8 MB", 
      status: "processing", 
      chunks: 0, 
      questions: 0,
      uploadedAt: "2024-01-20",
      lastQueried: "Never"
    },
    { 
      id: "doc_3", 
      name: "Company Policies.md", 
      type: "Markdown", 
      size: "456 KB", 
      status: "processed", 
      chunks: 12, 
      questions: 8,
      uploadedAt: "2024-01-10",
      lastQueried: "1 hour ago"
    },
  ]

  const recentQuestions = [
    { id: "q1", question: "What is the API rate limit?", document: "API Documentation.pdf", answer: "1000 requests per hour", timestamp: "2 minutes ago" },
    { id: "q2", question: "How to reset a user password?", document: "Product Manual.docx", answer: "Use the password reset endpoint...", timestamp: "15 minutes ago" },
    { id: "q3", question: "What is our vacation policy?", document: "Company Policies.md", answer: "Employees get 20 days annually...", timestamp: "1 hour ago" },
  ]

  const stats = [
    { title: "Total Documents", value: "24", change: "+3 this week" },
    { title: "Text Chunks", value: "1,247", change: "+127 new chunks" },
    { title: "Q&A Pairs", value: "567", change: "+45 generated" },
    { title: "Total Queries", value: "2,847", change: "+247 today" },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Knowledge Base</h1>
          <p className="text-muted-foreground">Manage documents and enable AI-powered Q&A</p>
        </div>
        <Button className="gap-2">
          <Upload className="w-4 h-4" />
          Upload Document
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">{stat.change}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common knowledge base operations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Button variant="outline" className="h-auto flex-col gap-2 p-4">
              <Upload className="w-6 h-6" />
              <span>Upload Documents</span>
            </Button>
            <Button variant="outline" className="h-auto flex-col gap-2 p-4">
              <Search className="w-6 h-6" />
              <span>Query Knowledge</span>
            </Button>
            <Button variant="outline" className="h-auto flex-col gap-2 p-4">
              <Brain className="w-6 h-6" />
              <span>Generate Q&A</span>
            </Button>
            <Button variant="outline" className="h-auto flex-col gap-2 p-4">
              <RefreshCw className="w-6 h-6" />
              <span>Reprocess All</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Base Management</CardTitle>
          <CardDescription>Manage your documents and knowledge base</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="documents" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="documents">Documents</TabsTrigger>
              <TabsTrigger value="queries">Recent Queries</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
              <TabsTrigger value="analytics">Analytics</TabsTrigger>
            </TabsList>
            
            <TabsContent value="documents" className="space-y-4">
              <div className="flex gap-2 mb-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input placeholder="Search documents..." className="pl-9" />
                </div>
                <Select>
                  <SelectTrigger className="w-32">
                    <SelectValue placeholder="Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="pdf">PDF</SelectItem>
                    <SelectItem value="docx">DOCX</SelectItem>
                    <SelectItem value="md">Markdown</SelectItem>
                    <SelectItem value="txt">Text</SelectItem>
                  </SelectContent>
                </Select>
                <Select>
                  <SelectTrigger className="w-32">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="processed">Processed</SelectItem>
                    <SelectItem value="processing">Processing</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Document</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Chunks</TableHead>
                    <TableHead>Q&A Pairs</TableHead>
                    <TableHead>Last Queried</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          <span className="font-medium">{doc.name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{doc.type}</Badge>
                      </TableCell>
                      <TableCell>{doc.size}</TableCell>
                      <TableCell>
                        <Badge variant={doc.status === "processed" ? "default" : doc.status === "processing" ? "secondary" : "destructive"}>
                          {doc.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{doc.chunks}</TableCell>
                      <TableCell>{doc.questions}</TableCell>
                      <TableCell>{doc.lastQueried}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-2 justify-end">
                          <Button variant="ghost" size="sm">
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <RefreshCw className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TabsContent>
            
            <TabsContent value="queries" className="space-y-4">
              <div className="space-y-4">
                {recentQuestions.map((query) => (
                  <Card key={query.id}>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <MessageSquare className="w-4 h-4 text-blue-500" />
                            <span className="font-medium">{query.question}</span>
                          </div>
                          <span className="text-xs text-muted-foreground">{query.timestamp}</span>
                        </div>
                        <div className="pl-6">
                          <p className="text-sm text-muted-foreground mb-1">Answer:</p>
                          <p className="text-sm">{query.answer}</p>
                          <div className="flex items-center gap-1 mt-2">
                            <BookOpen className="w-3 h-3 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">Source: {query.document}</span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
            
            <TabsContent value="settings" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Processing Settings</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Chunk Size</span>
                      <span className="text-sm text-muted-foreground">1000 characters</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Chunk Overlap</span>
                      <span className="text-sm text-muted-foreground">200 characters</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Auto Q&A Generation</span>
                      <Badge variant="default">Enabled</Badge>
                    </div>
                    <Button variant="outline" size="sm" className="w-full">
                      Configure Processing
                    </Button>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Embedding Settings</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Provider</span>
                      <Badge variant="secondary">OpenAI</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Model</span>
                      <span className="text-sm text-muted-foreground">text-embedding-3-small</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Vector Database</span>
                      <Badge variant="secondary">MongoDB Atlas</Badge>
                    </div>
                    <Button variant="outline" size="sm" className="w-full">
                      Configure Embeddings
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="analytics" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Query Performance</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">285ms</div>
                    <div className="text-sm text-muted-foreground">Average response time</div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Most Queried Document</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold">API Documentation</div>
                    <div className="text-sm text-muted-foreground">142 queries this week</div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Question Categories</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm">API Questions</span>
                        <span className="text-sm text-muted-foreground">45%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">Policy Questions</span>
                        <span className="text-sm text-muted-foreground">30%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">Product Questions</span>
                        <span className="text-sm text-muted-foreground">25%</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
} 