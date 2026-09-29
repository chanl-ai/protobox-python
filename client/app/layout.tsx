import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "@/components/providers";
import { AppLoader } from "@/components/app-loader";
import { UniversalLoadingDialog } from "@/components/universal-loading-dialog";
import { TopLoadingBar } from "@/components/top-loading-bar";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ProtoBox - Build AI Tools Without Code",
  description: "Connect your data, APIs, and workflows to ChatGPT, Claude, and other AI assistants.",
  icons: {
    icon: '/favicon.ico',
  },
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>
          <AppLoader>
            <TopLoadingBar />
            {children}
            <UniversalLoadingDialog />
          </AppLoader>
        </Providers>
        <Toaster 
          position="top-center"
          toastOptions={{
            classNames: {
              error: 'bg-red-600 text-white border-red-600',
              success: 'bg-green-600 text-white border-green-600',
              warning: 'bg-yellow-600 text-white border-yellow-600',
              info: 'bg-blue-600 text-white border-blue-600',
            },
          }}
        />
      </body>
    </html>
  );
}
