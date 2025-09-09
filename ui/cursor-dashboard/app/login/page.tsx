'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [passcode, setPasscode] = useState('')
  const [error, setError] = useState('')
  const router = useRouter()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Check passcode (default: 'changeme')
    const correctPasscode = process.env.NEXT_PUBLIC_DEMO_PASSCODE || 'changeme'
    
    if (passcode === correctPasscode) {
      // Set authentication cookie
      document.cookie = 'demo-authenticated=true; path=/; max-age=86400' // 24 hours
      router.push('/')
    } else {
      setError('Invalid passcode. Please try again.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            ACD Monitor Demo
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Enter the demo passcode to access the dashboard
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="passcode" className="sr-only">
              Demo Passcode
            </label>
            <input
              id="passcode"
              name="passcode"
              type="password"
              required
              className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
              placeholder="Enter demo passcode"
              value={passcode}
              onChange={(e) => setPasscode(e.target.value)}
            />
          </div>
          
          {error && (
            <div className="text-red-600 text-sm text-center">
              {error}
            </div>
          )}

          <div>
            <button
              type="submit"
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Access Dashboard
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
