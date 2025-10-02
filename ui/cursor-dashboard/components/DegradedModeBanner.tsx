"use client"

import { AlertTriangle } from "lucide-react"

interface DegradedModeBannerProps {
  isVisible: boolean
  lastHeartbeat?: number
}

export function DegradedModeBanner({ isVisible, lastHeartbeat }: DegradedModeBannerProps) {
  if (!isVisible) return null

  const heartbeatText = lastHeartbeat 
    ? `Last backend heartbeat: ${lastHeartbeat}s ago`
    : "Backend connection unavailable"

  return (
    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 mb-4">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />
        <div className="text-sm text-amber-200">
          <div className="font-medium">Data delayed/stale. Some tiles may be approximate.</div>
          <div className="text-xs text-amber-300/80 mt-1">{heartbeatText}</div>
        </div>
      </div>
    </div>
  )
}
