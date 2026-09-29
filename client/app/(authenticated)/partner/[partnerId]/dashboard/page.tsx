"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Users, Zap, TrendingUp, DollarSign, Settings, Copy, Loader2 } from "lucide-react"
import { partnerApi } from "@/lib/api/partners"
import type { PartnerStats, PartnerCustomer } from "@/lib/api/partners"
import { useAuth } from "@/lib/auth"

interface PartnerDashboardProps {
  params: Promise<{ partnerId: string }>
}

export default function PartnerDashboard({ params }: PartnerDashboardProps) {
  const [partnerId, setPartnerId] = useState<string>('')
  
  useEffect(() => {
    params.then(p => setPartnerId(p.partnerId))
  }, [params])
  const { user } = useAuth()
  const [stats, setStats] = useState<PartnerStats | null>(null)
  const [customers, setCustomers] = useState<PartnerCustomer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchPartnerData = async () => {
      if (!user?.customToken) return

      try {
        setLoading(true)

        // Fetch stats and customers in parallel
        const [stats, customers] = await Promise.all([
          partnerApi.getPartnerStats(partnerId),
          partnerApi.getPartnerCustomers(partnerId)
        ])

        setStats(stats)
        setCustomers(customers)
      } catch (err) {
        setError('Failed to load partner data')
      } finally {
        setLoading(false)
      }
    }

    fetchPartnerData()
  }, [user?.customToken, partnerId])

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Partner Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Welcome to your ProtoBox partner portal
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="font-mono text-xs">
            {partnerId}
          </Badge>
          <Button size="sm" variant="outline">
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Customers</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{stats?.total_customers || 0}</div>
            )}
            {loading ? (
              <Skeleton className="h-3 w-20 mt-1" />
            ) : (
              <p className="text-xs text-muted-foreground">
                {stats?.last_30_days_growth?.customers ? 
                  `+${(stats.last_30_days_growth.customers * 100).toFixed(0)}%` : 
                  '+0%'} from last month
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Integrations</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{stats?.active_integrations || 0}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Across all customers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Requests</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{formatNumber(stats?.monthly_requests || 0)}</div>
            )}
            {loading ? (
              <Skeleton className="h-3 w-20 mt-1" />
            ) : (
              <p className="text-xs text-muted-foreground">
                {stats?.last_30_days_growth?.requests ? 
                  `+${(stats.last_30_days_growth.requests * 100).toFixed(0)}%` : 
                  '+0%'} from last month
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{formatCurrency(stats?.revenue || 0)}</div>
            )}
            {loading ? (
              <Skeleton className="h-3 w-20 mt-1" />
            ) : (
              <p className="text-xs text-muted-foreground">
                {stats?.last_30_days_growth?.revenue ? 
                  `+${(stats.last_30_days_growth.revenue * 100).toFixed(0)}%` : 
                  '+0%'} from last month
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Customers */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Customers</CardTitle>
          <CardDescription>
            Latest customers added to your partner account
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Skeleton className="w-10 h-10 rounded-lg" />
                    <div>
                      <Skeleton className="h-4 w-24 mb-1" />
                      <Skeleton className="h-3 w-20" />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-5 w-12" />
                    <Skeleton className="h-8 w-12" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-8 text-muted-foreground">
              {error}
            </div>
          ) : customers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No customers yet. Start by creating your first tenant workspace.
            </div>
          ) : (
            <div className="space-y-4">
              {customers.slice(0, 5).map((customer) => (
                <div key={customer.tenant_id} className="flex items-center justify-between border-b border-border/40 pb-4 last:border-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                      <Users className="w-5 h-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{customer.customer_name || `Customer ${customer.tenant_id}`}</p>
                      <p className="text-sm text-muted-foreground">
                        {customer.integrations_count} integrations • {formatNumber(customer.total_requests)} requests
                      </p>  
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={customer.status === 'active' ? 'default' : 'secondary'}>
                      {customer.status}
                    </Badge>
                    <Button size="sm" variant="ghost">
                      View
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common partner management tasks
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            <Button variant="outline" className="justify-start h-auto p-4">
              <Users className="w-4 h-4 mr-2" />
              <div className="text-left">
                <div className="font-medium">Add Customer</div>
                <div className="text-xs text-muted-foreground">Create new tenant workspace</div>
              </div>
            </Button>
            
            <Button variant="outline" className="justify-start h-auto p-4">
              <Copy className="w-4 h-4 mr-2" />
              <div className="text-left">
                <div className="font-medium">API Credentials</div>
                <div className="text-xs text-muted-foreground">View and manage keys</div>
              </div>
            </Button>
            
            <Button variant="outline" className="justify-start h-auto p-4">
              <TrendingUp className="w-4 h-4 mr-2" />
              <div className="text-left">
                <div className="font-medium">View Analytics</div>
                <div className="text-xs text-muted-foreground">Usage and performance</div>
              </div>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}