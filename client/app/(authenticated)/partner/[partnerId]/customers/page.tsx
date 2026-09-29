import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Users, Search, Plus, ExternalLink, Settings } from "lucide-react"

interface PartnerCustomersProps {
  params: Promise<{ partnerId: string }>
}

export default async function PartnerCustomers({ params }: PartnerCustomersProps) {
  const { partnerId } = await params

  // Dummy customer data
  const customers = [
    {
      id: "cust_001",
      name: "ACME Voice AI",
      workspaceId: "ws_acme_123",
      integrations: 5,
      lastActive: "2 hours ago",
      status: "active",
      totalRequests: "45.2K"
    },
    {
      id: "cust_002", 
      name: "TechFlow Solutions",
      workspaceId: "ws_techflow_456",
      integrations: 3,
      lastActive: "1 day ago", 
      status: "active",
      totalRequests: "23.1K"
    },
    {
      id: "cust_003",
      name: "DataStream Corp", 
      workspaceId: "ws_datastream_789",
      integrations: 2,
      lastActive: "3 days ago",
      status: "pending",
      totalRequests: "8.7K" 
    },
    {
      id: "cust_004",
      name: "CloudVoice Inc",
      workspaceId: "ws_cloudvoice_012", 
      integrations: 7,
      lastActive: "5 minutes ago",
      status: "active", 
      totalRequests: "89.5K"
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Partner Customers</h1>
          <p className="text-muted-foreground mt-1">
            Manage workspaces for your partner customers
          </p>
        </div>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Add Customer
        </Button>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            placeholder="Search customers..."
            className="pl-10"
          />
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{customers.length} customers</Badge>
        </div>
      </div>

      {/* Customers List */}
      <Card>
        <CardHeader>
          <CardTitle>Customer Workspaces</CardTitle>
          <CardDescription>
            Each customer gets their own isolated workspace with integrations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {customers.map((customer) => (
              <div key={customer.id} className="flex items-center justify-between p-4 border border-border/40 rounded-lg hover:bg-muted/50 transition-colors">
                <div className="flex items-center gap-4">
                  {/* Customer Icon */}
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Users className="w-6 h-6 text-primary" />
                  </div>
                  
                  {/* Customer Info */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{customer.name}</h3>
                      <Badge variant={customer.status === 'active' ? 'default' : 'secondary'}>
                        {customer.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>ID: {customer.id}</span>
                      <span>•</span>
                      <span>Workspace: {customer.workspaceId}</span>
                      <span>•</span>
                      <span>Last active: {customer.lastActive}</span>
                    </div>
                  </div>
                </div>

                {/* Customer Stats */}
                <div className="flex items-center gap-6">
                  <div className="text-center">
                    <div className="text-lg font-semibold">{customer.integrations}</div>
                    <div className="text-xs text-muted-foreground">Integrations</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold">{customer.totalRequests}</div>
                    <div className="text-xs text-muted-foreground">Requests</div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline">
                      <ExternalLink className="w-4 h-4 mr-1" />
                      View Workspace
                    </Button>
                    <Button size="sm" variant="ghost">
                      <Settings className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Customer Creation Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Add New Customer</CardTitle>
          <CardDescription>
            Use the ProtoBox Partner SDK to programmatically create customer workspaces
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-muted/50 rounded-lg p-4 font-mono text-sm">
            <div className="text-muted-foreground mb-2"># Python SDK Example</div>
            <div>
              <span className="text-blue-600">from</span> protobox <span className="text-blue-600">import</span> ProtoBoxClient<br/>
              <br/>
              client = ProtoBoxClient(<br/>
              &nbsp;&nbsp;partner_id=<span className="text-green-600">"{partnerId}"</span>,<br/>
              &nbsp;&nbsp;secret_key=<span className="text-green-600">"your_secret_key"</span><br/>
              )<br/>
              <br/>
              <span className="text-purple-600">workspace</span> = <span className="text-blue-600">await</span> client.create_tenant(<br/>
              &nbsp;&nbsp;tenant_id=<span className="text-green-600">"customer_123"</span>,<br/>
              &nbsp;&nbsp;tenant_name=<span className="text-green-600">"Customer Company"</span><br/>
              )
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}