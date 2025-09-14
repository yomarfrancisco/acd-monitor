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
  title: `NinjaA — v3 ${process.env.VERCEL_GIT_COMMIT_SHA?.slice(0,7) || 'no-sha'}`,
  description: "Recreation of Cursor AI Dashboard",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="h-full dark" data-build-sha={process.env.VERCEL_GIT_COMMIT_SHA} data-env={process.env.VERCEL_ENV}>
      <body className={`min-h-full antialiased ${inter.variable}`} data-probe="root-layout">
        {/* beacon TEMP off */}
        {/* <div
          data-ssr-beacon="v3"
          style={{position:'fixed',top:0,left:0,right:0,zIndex:99999,background:'#ff0000',color:'#fff',padding:'8px',fontWeight:700,textAlign:'center'}}
        >
          BEACON v3 — root app/layout.tsx — {process.env.VERCEL_GIT_COMMIT_SHA?.slice(0,7) ?? 'no-sha'}
        </div> */}
        
        <Suspense fallback={null}>{children}</Suspense>
        
        {/* Build SHA in footer */}
        <div style={{position:'fixed',bottom:0,left:0,background:'#333',color:'#fff',padding:'4px 8px',fontSize:10,zIndex:99999}}>
          build: {process.env.VERCEL_GIT_COMMIT_SHA}
        </div>
      </body>
    </html>
  )
}
