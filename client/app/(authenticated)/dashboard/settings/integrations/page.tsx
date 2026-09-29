import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Globe } from "lucide-react"

export default function IntegrationsSettingsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Integrations</CardTitle>
        <CardDescription>
          Connect with third-party services and tools
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-center py-12">
          <Globe className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">Third-Party Integrations</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Connect your account with external services and applications.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}