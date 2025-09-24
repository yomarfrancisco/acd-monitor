"use client"

import React, { createContext, useContext, useState, ReactNode } from 'react'

interface ExchangeDataContextType {
  exchangeData: any[]
  setExchangeData: (data: any[]) => void
  exchangeDataLoading: boolean
  setExchangeDataLoading: (loading: boolean) => void
  exchangeDataError: string | null
  setExchangeDataError: (error: string | null) => void
}

const ExchangeDataContext = createContext<ExchangeDataContextType | undefined>(undefined)

export function ExchangeDataProvider({ children }: { children: ReactNode }) {
  const [exchangeData, setExchangeData] = useState<any[]>([])
  const [exchangeDataLoading, setExchangeDataLoading] = useState(false)
  const [exchangeDataError, setExchangeDataError] = useState<string | null>(null)

  return (
    <ExchangeDataContext.Provider value={{
      exchangeData,
      setExchangeData,
      exchangeDataLoading,
      setExchangeDataLoading,
      exchangeDataError,
      setExchangeDataError
    }}>
      {children}
    </ExchangeDataContext.Provider>
  )
}

export function useExchangeData() {
  const context = useContext(ExchangeDataContext)
  if (context === undefined) {
    throw new Error('useExchangeData must be used within an ExchangeDataProvider')
  }
  return context
}
