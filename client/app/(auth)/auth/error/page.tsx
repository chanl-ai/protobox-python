import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default function AuthErrorPage() {
  return (
    <Card className="overflow-hidden p-0">
      <CardContent className="grid p-0 md:grid-cols-1">
        <div className="p-6 md:p-8">
          <div className="flex flex-col gap-6">
            <div className="flex flex-col items-center text-center">
              <h1 className="text-2xl font-bold">Authentication Error</h1>
              <p className="text-muted-foreground text-balance">
                There was an error during the authentication process
              </p>
            </div>
            <div className="text-center text-sm text-muted-foreground">
              <p>
                This could be due to an expired link, invalid credentials, or a temporary issue. 
                Please try again or contact support if the problem persists.
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <Button asChild className="w-full">
                <Link href="/login">
                  Back to Login
                </Link>
              </Button>
              <Button asChild variant="outline" className="w-full">
                <Link href="/signup">
                  Create New Account
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}