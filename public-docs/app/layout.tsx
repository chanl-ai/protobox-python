import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Mocopo Documentation',
  description: 'Model Context Protocol (MCP) server documentation for Mocopo',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}