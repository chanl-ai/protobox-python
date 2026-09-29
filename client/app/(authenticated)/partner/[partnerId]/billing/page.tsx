"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/ui/page-header"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Label } from "@/components/ui/label"
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { 
  DollarSign,
  CreditCard,
  Download,
  TrendingUp,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Clock,
  Receipt,
  Settings
} from "lucide-react"

// Dummy billing data
const mockBillingData = {
  currentPlan: {
    name: "Partner Pro",
    price: 299,
    billing: "monthly",
    features: [
      "Unlimited API requests",
      "Advanced analytics",
      "Priority support",
      "Custom branding",
      "Team collaboration"
    ]
  },
  usage: {
    requests: 48750,
    requestsLimit: 100000,
    workspaces: 23,
    workspacesLimit: 50,
    teamMembers: 4,
    teamMembersLimit: 10
  },
  revenue: {
    thisMonth: 15420,
    lastMonth: 13280,
    growth: 16.1,
    ytd: 142350
  }
}

const mockInvoices = [
  {
    id: "inv_001",
    date: "2024-07-01",
    amount: 299.00,
    status: "paid",
    description: "Partner Pro - July 2024",
    paymentMethod: "•••• 4242"
  },
  {
    id: "inv_002",
    date: "2024-06-01", 
    amount: 299.00,
    status: "paid",
    description: "Partner Pro - June 2024",
    paymentMethod: "•••• 4242"
  },
  {
    id: "inv_003",
    date: "2024-05-01",
    amount: 299.00,
    status: "paid", 
    description: "Partner Pro - May 2024",
    paymentMethod: "•••• 4242"
  },
  {
    id: "inv_004",
    date: "2024-04-01",
    amount: 199.00,
    status: "paid",
    description: "Partner Basic - April 2024",
    paymentMethod: "•••• 4242"
  }
]

const mockPayouts = [
  {
    id: "payout_001",
    date: "2024-07-15",
    amount: 1542.00,
    status: "completed",
    period: "June 2024",
    method: "Bank Transfer"
  },
  {
    id: "payout_002", 
    date: "2024-06-15",
    amount: 1328.00,
    status: "completed",
    period: "May 2024", 
    method: "Bank Transfer"
  },
  {
    id: "payout_003",
    date: "2024-05-15",
    amount: 1156.00,
    status: "completed",
    period: "April 2024",
    method: "Bank Transfer"
  }
]

import { use } from "react"

interface BillingPageProps {
  params: Promise<{ partnerId: string }>
}

export default function BillingPage({ params }: BillingPageProps) {
  const { partnerId } = use(params)
  const [billingPeriod, setBillingPeriod] = useState("monthly")

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "paid":
      case "completed":
        return <Badge className="bg-green-100 text-green-800">
          <CheckCircle className="w-3 h-3 mr-1" />
          {status === "paid" ? "Paid" : "Completed"}
        </Badge>
      case "pending":
        return <Badge className="bg-yellow-100 text-yellow-800">
          <Clock className="w-3 h-3 mr-1" />
          Pending
        </Badge>
      case "failed":
        return <Badge className="bg-red-100 text-red-800">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Failed
        </Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const actions = [
    <Dialog key="upgrade">
      <DialogTrigger asChild>
        <Button variant="outline">
          <TrendingUp className="w-4 h-4 mr-2" />
          Upgrade Plan
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upgrade Your Plan</DialogTitle>
          <DialogDescription>
            Choose a plan that best fits your business needs
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <Card className="p-4">
              <h3 className="font-semibold">Partner Pro</h3>
              <p className="text-2xl font-bold">$299<span className="text-sm font-normal">/mo</span></p>
              <p className="text-sm text-muted-foreground">Current Plan</p>
            </Card>
            <Card className="p-4 border-blue-200">
              <h3 className="font-semibold">Partner Enterprise</h3>
              <p className="text-2xl font-bold">$599<span className="text-sm font-normal">/mo</span></p>
              <p className="text-sm text-blue-600">Recommended</p>
            </Card>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline">Cancel</Button>
          <Button>Upgrade to Enterprise</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>,
    <Button key="download">
      <Download className="w-4 h-4 mr-2" />
      Download Invoice
    </Button>
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Billing"
        subtitle="Manage your subscription, view usage, and track revenue"
        actions={actions}
      />

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${mockBillingData.revenue.thisMonth.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+{mockBillingData.revenue.growth}%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">YTD Revenue</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${mockBillingData.revenue.ytd.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Year to date earnings
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Plan</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockBillingData.currentPlan.name}</div>
            <p className="text-xs text-muted-foreground">
              ${mockBillingData.currentPlan.price}/month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Next Billing</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Aug 1</div>
            <p className="text-xs text-muted-foreground">
              In 7 days
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Current Plan */}
        <Card>
          <CardHeader>
            <CardTitle>Current Plan</CardTitle>
            <CardDescription>
              Your active subscription and usage
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">{mockBillingData.currentPlan.name}</h3>
                <p className="text-sm text-muted-foreground">
                  ${mockBillingData.currentPlan.price}/{mockBillingData.currentPlan.billing}
                </p>
              </div>
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Manage
              </Button>
            </div>

            <Separator />

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>API Requests</span>
                  <span>{mockBillingData.usage.requests.toLocaleString()} / {mockBillingData.usage.requestsLimit.toLocaleString()}</span>
                </div>
                <Progress value={(mockBillingData.usage.requests / mockBillingData.usage.requestsLimit) * 100} />
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Active Workspaces</span>
                  <span>{mockBillingData.usage.workspaces} / {mockBillingData.usage.workspacesLimit}</span>
                </div>
                <Progress value={(mockBillingData.usage.workspaces / mockBillingData.usage.workspacesLimit) * 100} />
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Team Members</span>
                  <span>{mockBillingData.usage.teamMembers} / {mockBillingData.usage.teamMembersLimit}</span>
                </div>
                <Progress value={(mockBillingData.usage.teamMembers / mockBillingData.usage.teamMembersLimit) * 100} />
              </div>
            </div>

            <Separator />

            <div>
              <h4 className="font-medium mb-2">Plan Features</h4>
              <ul className="space-y-1">
                {mockBillingData.currentPlan.features.map((feature, index) => (
                  <li key={index} className="flex items-center text-sm">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Revenue Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Revenue Summary</CardTitle>
            <CardDescription>
              Your partner program earnings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">This Month</Label>
                  <p className="text-2xl font-bold">${mockBillingData.revenue.thisMonth.toLocaleString()}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">Last Month</Label>
                  <p className="text-2xl font-bold">${mockBillingData.revenue.lastMonth.toLocaleString()}</p>
                </div>
              </div>

              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="font-medium text-green-800">Revenue Growth</p>
                    <p className="text-sm text-green-700">
                      +{mockBillingData.revenue.growth}% increase from last month
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h4 className="font-medium mb-3">Recent Payouts</h4>
                <div className="space-y-2">
                  {mockPayouts.slice(0, 3).map((payout) => (
                    <div key={payout.id} className="flex items-center justify-between p-2 border rounded">
                      <div>
                        <p className="font-medium text-sm">${payout.amount.toLocaleString()}</p>
                        <p className="text-xs text-muted-foreground">{payout.period}</p>
                      </div>
                      <div className="text-right">
                        {getStatusBadge(payout.status)}
                        <p className="text-xs text-muted-foreground">
                          {new Date(payout.date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Billing History */}
      <Card>
        <CardHeader>
          <CardTitle>Billing History</CardTitle>
          <CardDescription>
            View and download your invoices and payment history
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Payment Method</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockInvoices.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{invoice.id}</div>
                      <div className="text-sm text-muted-foreground">
                        {invoice.description}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {new Date(invoice.date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="font-medium">
                      ${invoice.amount.toFixed(2)}
                    </div>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(invoice.status)}
                  </TableCell>
                  <TableCell className="text-sm">
                    {invoice.paymentMethod}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm">
                      <Download className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Payment Method */}
      <Card>
        <CardHeader>
          <CardTitle>Payment Method</CardTitle>
          <CardDescription>
            Manage your payment information
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center space-x-3">
              <CreditCard className="h-8 w-8 text-gray-400" />
              <div>
                <p className="font-medium">•••• •••• •••• 4242</p>
                <p className="text-sm text-muted-foreground">Expires 12/2024</p>
              </div>
            </div>
            <Button variant="outline" size="sm">
              Update
            </Button>
          </div>

          <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start space-x-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
              <div>
                <p className="font-medium text-yellow-800">Card Expiring Soon</p>
                <p className="text-sm text-yellow-700">
                  Your payment method expires in 5 months. Update it to avoid service interruption.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}