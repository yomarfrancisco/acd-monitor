import type React from "react"
import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import { Suspense } from "react"
import "./globals.css"

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
})

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
}

export const metadata: Metadata = {
  title: "Cursor Dashboard",
  description: "Recreation of Cursor AI Dashboard",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="h-full dark">
      <body className={`min-h-full antialiased ${inter.variable}`}>
        <Suspense fallback={null}>{children}</Suspense>
      </body>
    </html>
  )
}
