import { Inter } from "next/font/google"
import "@/app/globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata = {
  title: "ProtoBox Integrations",
  description: "Connect your tools to enhance your workflow",
}

export default function EmbedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.className}>
      <head>
        <meta name="robots" content="noindex" />
      </head>
      <body className="min-h-screen bg-background">
        {children}
      </body>
    </html>
  )
}