import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CreditCard } from "lucide-react"

export default function BillingSettingsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Billing & Plans</CardTitle>
        <CardDescription>
          Manage your subscription and payment methods
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-center py-12">
          <CreditCard className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">Billing Management</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            View and manage your subscription plans and payment methods.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}