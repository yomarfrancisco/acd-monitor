import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Check if user is already authenticated
  const isAuthenticated = request.cookies.get('demo-authenticated')?.value === 'true'
  
  // Allow access to the login page and API routes
  if (request.nextUrl.pathname === '/login' || request.nextUrl.pathname.startsWith('/api/')) {
    return NextResponse.next()
  }
  
  // If not authenticated, redirect to login
  if (!isAuthenticated) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
