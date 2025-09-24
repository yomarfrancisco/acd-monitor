"use client"

import {
  Bot,
  ChevronDown,
  FileText,
  Zap,
  Send,
  Settings,
  Database,
  Activity,
  CreditCard,
  BarChart3,
  TrendingUp,
  Clock,
  Download,
  User,
  SquareChevronRight,
  SquarePlus,
  ShieldCheck,
  Upload,
  Cloud,
  Brain,
  Target,
  Shield,
  Link,
  Gauge,
  Moon,
  Scale,
  Search,
} from "lucide-react"

import { Separator } from "@/components/ui/separator"
import Image from "next/image"

import { useState, useEffect, useRef, useMemo } from "react"
import * as React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AssistantBubble } from "@/components/AssistantBubble"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid, ReferenceLine, Label } from "recharts"
import { CalendarIcon, Copy, RefreshCw, ImageUp, Camera, FolderClosed, Github, AlertTriangle, Factory } from "lucide-react"
import { RiskSummarySchema, MetricsOverviewSchema, HealthRunSchema, EventsResponseSchema, DataSourcesSchema, EvidenceExportSchema, BinanceOverviewSchema } from "@/types/api.schemas"
import { fetchTyped } from "@/lib/backendAdapter"
import { safe } from "@/lib/safe"
import { resilientFetch } from "@/lib/resilient-api"
import { DegradedModeBanner } from "@/components/DegradedModeBanner"
import { EventsTable } from "@/components/EventsTable"
import { SelftestIndicator } from "@/components/SelftestIndicator"
import { useExchangeData } from "../contexts/ExchangeDataContext"
import { getAvailableUiVenues, uiKeyToDataKey, type UiVenue } from "../lib/venueMapping"
import { computePriceLeadership, type DataKey } from "../lib/leadership"
import type { RiskSummary, HealthRun, EventsResponse, DataSources, EvidenceExport } from "@/types/api"
import type { MetricsOverview } from "@/types/api.schemas"
import {
  MessageSquare,
  GitBranch,
  ClipboardList,
  CloudUpload,
  CalendarCheck2,
  ScaleIcon,
  SquarePen,
} from "lucide-react"

// Different data sets for different time periods
const analyticsData30d = [
  { date: "Aug 6", fnb: 100, absa: 95, standard: 105, nedbank: 98 },
  { date: "Aug 13", fnb: 150, absa: 145, standard: 155, nedbank: 148 },
  { date: "Aug 20", fnb: 200, absa: 190, standard: 210, nedbank: 195 },
  { date: "Aug 27", fnb: 250, absa: 240, standard: 260, nedbank: 245 },
  { date: "Sep 3", fnb: 300, absa: 290, standard: 310, nedbank: 295 },
  { date: "Sep 10", fnb: 350, absa: 330, standard: 370, nedbank: 340 },
]

const analyticsData6m = [
  { date: "Mar '25", fnb: 80, absa: 75, standard: 85, nedbank: 78 },
  { date: "Apr '25", fnb: 120, absa: 115, standard: 125, nedbank: 118 },
  { date: "May '25", fnb: 180, absa: 175, standard: 185, nedbank: 178 },
  { date: "Jun '25", fnb: 220, absa: 210, standard: 230, nedbank: 215 },
  { date: "Jul '25", fnb: 280, absa: 270, standard: 290, nedbank: 275 },
  { date: "Aug '25", fnb: 320, absa: 310, standard: 330, nedbank: 315 },
  { date: "Sep '25", fnb: 350, absa: 330, standard: 370, nedbank: 340 },
]

const analyticsData1y = [
  { date: "Sep '24", fnb: 60, absa: 55, standard: 65, nedbank: 58 },
  { date: "Oct '24", fnb: 80, absa: 75, standard: 85, nedbank: 78 },
  { date: "Nov '24", fnb: 100, absa: 95, standard: 105, nedbank: 98 },
  { date: "Dec '24", fnb: 120, absa: 115, standard: 125, nedbank: 118 },
  { date: "Jan '25", fnb: 140, absa: 135, standard: 145, nedbank: 138 },
  { date: "Feb '25", fnb: 180, absa: 175, standard: 185, nedbank: 178 },
  { date: "Mar '25", fnb: 220, absa: 210, standard: 230, nedbank: 215 },
  { date: "Apr '25", fnb: 260, absa: 250, standard: 270, nedbank: 255 },
  { date: "May '25", fnb: 300, absa: 290, standard: 310, nedbank: 295 },
  { date: "Jun '25", fnb: 320, absa: 310, standard: 330, nedbank: 315 },
  { date: "Jul '25", fnb: 340, absa: 330, standard: 350, nedbank: 335 },
  { date: "Aug '25", fnb: 360, absa: 350, standard: 370, nedbank: 355 },
  { date: "Sep '25", fnb: 350, absa: 330, standard: 370, nedbank: 340 },
]

const analyticsDataYTD = [
  { date: "Jan '25", fnb: 100, absa: 95, standard: 105, nedbank: 98 },
  { date: "Feb '25", fnb: 150, absa: 145, standard: 155, nedbank: 148 },
  { date: "Mar '25", fnb: 200, absa: 190, standard: 210, nedbank: 195 },
  { date: "Apr '25", fnb: 180, absa: 175, standard: 185, nedbank: 178 },
  { date: "May '25", fnb: 250, absa: 240, standard: 260, nedbank: 245 },
  { date: "Jun '25", fnb: 300, absa: 290, standard: 310, nedbank: 295 },
  { date: "Jul '25", fnb: 280, absa: 270, standard: 290, nedbank: 275 },
  { date: "Aug '25", fnb: 400, absa: 380, standard: 420, nedbank: 390 },
  { date: "Sep '25", fnb: 350, absa: 330, standard: 370, nedbank: 340 },
]

// Financial Compliance Dashboard - Main Component (CI Test)
// Dashboard button styling - keep original sizing, only change colors
const dashboardBtnClass = "border-[#AFC8FF] text-black bg-[#AFC8FF] hover:bg-[#9FBCFF] text-[9px] h-5 px-2 font-normal"

// Dashboard CTA button styling - pastel blue bg + black text for the 13 specific CTA buttons
const dashboardCtaBtnClass = "bg-[#AFC8FF] text-black hover:bg-[#9FBCFF] active:bg-[#95B4FF] ring-1 ring-inset ring-[#8FB3FF]/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6FA0FF] shadow-sm text-[9px] h-5 px-2 font-normal rounded-full disabled:bg-[#AFC8FF]/60 disabled:text-black/60 disabled:ring-[#8FB3FF]/50 disabled:cursor-not-allowed disabled:opacity-100"

// Custom hook for auto-resizing textarea
function useAutosizeTextarea(
  ref: React.RefObject<HTMLTextAreaElement>,
  value: string,
  opts: { minPx?: number; maxVh?: number } = {}
) {
  const { minPx = 112, maxVh = 40 } = opts;

  React.useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    // apply min/max every run (cheap & avoids CSS drift)
    el.style.minHeight = `${minPx}px`;
    el.style.maxHeight = `${maxVh}vh`;

    // measure -> grow to content, clamped by CSS max-height
    el.style.height = "auto";
    const next = el.scrollHeight;
    el.style.height = next + "px";

    // show scrollbar only when clamped
    const computed = getComputedStyle(el);
    const maxPx = parseFloat(computed.maxHeight);
    el.style.overflowY = el.scrollHeight > maxPx ? "auto" : "hidden";
  }, [ref, value, minPx, maxVh]);

  // keep height sensible on viewport changes
  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onResize = () => {
      el.style.height = "auto";
      el.style.height = el.scrollHeight + "px";
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [ref]);
}

export default function CursorDashboard() {
  const [activeTab, setActiveTab] = useState<"agents" | "dashboard">("agents")
  const [selectedTimeframe, setSelectedTimeframe] = useState<"30d" | "6m" | "1y" | "ytd">("ytd")
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)
  const [isDesktop, setIsDesktop] = useState(false)
  const [isInputFocused, setIsInputFocused] = useState(false)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Helper function to truncate text to specified length
  const truncateText = (text: string, maxLength: number = 40) => {
    return text.length > maxLength ? text.slice(0, maxLength - 1).trimEnd() + "…" : text;
  };

  // Series adapter: convert exchange data to chart format
  const createChartSeries = (successfulExchanges: any[]) => {
    // Build authoritative "what's available" list from live results
    const availableUiVenues: UiVenue[] = getAvailableUiVenues(successfulExchanges)
    
    // Debug logging
    if (process.env.NEXT_PUBLIC_UI_DEBUG === 'true') {
      console.log('SERIES_VENUES=', availableUiVenues);
    }
    
    // Create a map of all timestamps to ensure alignment
    const allTimestamps = new Set<string>()
    successfulExchanges.forEach(exchange => {
      if (exchange.data?.ohlcv) {
        exchange.data.ohlcv.forEach((bar: any[]) => {
          allTimestamps.add(bar[0]) // ISO timestamp
        })
      }
    })
    
    const sortedTimestamps = Array.from(allTimestamps).sort()
    
    // Create chart data points - keep the old shape, fill only present series
    const chartData = sortedTimestamps.map(timestamp => {
      const point: any = { date: new Date(timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }
      
      // Only populate keys that exist in availableUiVenues
      for (const uiVenue of availableUiVenues) {
        const dataKey = uiKeyToDataKey[uiVenue]
        
        // Find the corresponding exchange for this UI venue
        const exchange = successfulExchanges.find(e => {
          const venueMapping: Record<string, string> = {
            'binance': 'binance',
            'okx': 'coinbase',
            'bybit': 'bybit', 
            'kraken': 'kraken'
          }
          return venueMapping[e.venue] === uiVenue
        })
        
        if (exchange?.data?.ohlcv) {
          // Find the bar for this timestamp
          const bar = exchange.data.ohlcv.find((b: any[]) => b[0] === timestamp)
          if (bar) {
            // Use close price (index 4) as the value
            point[dataKey] = Number(bar[4]) || 0
          }
        }
      }
      
      return point
    })
    
    return chartData
  }
  
  // Risk summary state
  const [riskSummary, setRiskSummary] = useState<RiskSummary | null>(null)
  const [riskSummaryLoading, setRiskSummaryLoading] = useState(false)
  const [riskSummaryError, setRiskSummaryError] = useState<string | null>(null)
  
  // Metrics overview state
  const [metricsOverview, setMetricsOverview] = useState<MetricsOverview | null>(null)
  const [metricsLoading, setMetricsLoading] = useState(false)
  const [metricsError, setMetricsError] = useState<string | null>(null)
  
  // Exchange data state for live chart (using context)
  const { exchangeData, setExchangeData, exchangeDataLoading, setExchangeDataLoading, exchangeDataError, setExchangeDataError, availableUiVenues, setAvailableUiVenues } = useExchangeData()
  
  // Health run state
  const [healthRun, setHealthRun] = useState<HealthRun | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState<string | null>(null)
  
  // Events state
  const [events, setEvents] = useState<EventsResponse | null>(null)
  const [eventsLoading, setEventsLoading] = useState(false)
  const [eventsError, setEventsError] = useState<string | null>(null)
  
  // Data sources state
  const [dataSources, setDataSources] = useState<DataSources | null>(null)
  const [dataSourcesLoading, setDataSourcesLoading] = useState(false)
  const [dataSourcesError, setDataSourcesError] = useState<string | null>(null)
  
  // Evidence export state
  const [evidenceExport, setEvidenceExport] = useState<EvidenceExport | null>(null)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)
  
  // Degraded mode state
  const [isDegradedMode, setIsDegradedMode] = useState(false)
  const [lastHeartbeat, setLastHeartbeat] = useState<number | null>(null)

  // Evidence export handler
  const handleEvidenceExport = async () => {
    setEvidenceLoading(true)
    setEvidenceError(null)
    
    try {
      // Use resilient fetch for evidence export with longer timeout
      const response = await fetch('/api/evidence/export', { 
        method: 'GET',
        signal: AbortSignal.timeout(30000) // 30 second timeout for file generation
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      // Try to read filename from header; fallback if absent
      const cd = response.headers.get('content-disposition') || ''
      const match = cd.match(/filename="?(.+?)"?$/)
      const fname = match?.[1] ?? 'acd-evidence.zip'

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fname
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      
      setEvidenceExport({
        requestedAt: new Date().toISOString(),
        status: 'READY',
        bundleId: fname.replace('.zip', ''),
        url: url
      })
      
      console.log('Evidence package downloaded successfully')
    } catch (error) {
      console.error('Evidence export failed', error)
      const errorMessage = error instanceof Error ? error.message : 'Failed to export evidence'
      setEvidenceError(errorMessage)
      console.error(`Evidence export failed: ${errorMessage}`)
    } finally {
      setEvidenceLoading(false)
    }
  }
  const [selectedDate, setSelectedDate] = useState<{ from: Date | undefined; to?: Date | undefined } | undefined>({
    from: new Date(),
    to: new Date(),
  })
  const [isClient, setIsClient] = useState(false)
  const [inputValue, setInputValue] = useState("")
  const [activeSidebarItem, setActiveSidebarItem] = useState<
    | "overview"
    | "configuration"
    | "data-sources"
    | "ai-economists"
    | "health-checks"
    | "events-log"
    | "billing"
    | "compliance"
    | "contact"
  >("overview")

  // Add state for selected agent type
  const [selectedAgent, setSelectedAgent] = useState("Europe")
  const [selectedIndustry, setSelectedIndustry] = useState("Crypto")
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([])

  // Helper function to map region names to acronyms
  const getRegionAcronym = (regionName: string): string => {
    const mapping: Record<string, string> = {
      "Europe": "EU",
      "South Africa": "SA", 
      "United States": "USA",
      "Australia": "AUS"
    }
    return mapping[regionName] || "EU"
  }

  // Helper function to map industry names to acronyms
  const getIndustryAcronym = (industryName: string): string => {
    const mapping: Record<string, string> = {
      "All": "All",
      "Travel & Hospitality": "Travel",
      "E-commerce": "E-com",
      "Shipping & Logistics": "Logistics",
      "Media & Advertising": "Media",
      "Real-Estate": "Real",
      "Telecommunications": "Telecom",
      "Financial services": "Finance"
    }
    return mapping[industryName] || "Crypto"
  }

  // Configuration input field states
  const [changeThreshold, setChangeThreshold] = useState("5%")
  const [confidenceLevel, setConfidenceLevel] = useState("95%")
  const [updateFrequency, setUpdateFrequency] = useState("5m")
  const [sensitivityLevel, setSensitivityLevel] = useState("Medium")
  const [maxDataAge, setMaxDataAge] = useState("10m")
  const [autoDetectMarketChanges, setAutoDetectMarketChanges] = useState(true)
  const [enableLiveMonitoring, setEnableLiveMonitoring] = useState(true)
  const [checkDataQuality, setCheckDataQuality] = useState(true)
  const [bloombergDataFeed, setBloombergDataFeed] = useState(false)
  const [showEventModal, setShowEventModal] = useState(false)
  const [initialAgentMessage, setInitialAgentMessage] = useState("")
  const [messages, setMessages] = useState<
    Array<{ id: string; type: "user" | "agent"; content: string; timestamp: Date }>
  >([])
  const [hasEngaged, setHasEngaged] = useState<boolean>(false)
  const [isAssistantTyping, setIsAssistantTyping] = useState<boolean>(false)
  
  // track whether at least one user message has been sent in this session
  const [hasStartedChat, setHasStartedChat] = useState(false)

  // if you already have `messages` state, you can also derive it:
  const chatStartedFromHistory = useMemo(
    () => messages?.some(m => m.type === 'user') ?? false,
    [messages]
  )

  // prefer explicit flip on first send; keep derived as safety net
  const chatStarted = hasStartedChat || chatStartedFromHistory
  
  // Upload menu state
  const [isUploadMenuOpen, setIsUploadMenuOpen] = useState<boolean>(false)
  const [uploadMenuAnchorRef, setUploadMenuAnchorRef] = useState<HTMLButtonElement | null>(null)
  const [uploadMenuFocusIndex, setUploadMenuFocusIndex] = useState<number>(-1)
  const [isGitHubModalOpen, setIsGitHubModalOpen] = useState<boolean>(false)
  const [gitHubRepoUrl, setGitHubRepoUrl] = useState<string>("")
  
  // Role dropdown state
  const [isRoleDropdownOpen, setIsRoleDropdownOpen] = useState<boolean>(false)
  const [roleDropdownFocusIndex, setRoleDropdownFocusIndex] = useState<number>(-1)

  // Industry dropdown state
  const [isIndustryDropdownOpen, setIsIndustryDropdownOpen] = useState<boolean>(false)
  const [industryDropdownFocusIndex, setIndustryDropdownFocusIndex] = useState<number>(-1)
  
  // Dual-trigger dropdown refs and state
  const triggerClusterRef = useRef<HTMLDivElement | null>(null)
  const triggerIconRef = useRef<HTMLButtonElement | null>(null)
  const triggerTextRef = useRef<HTMLButtonElement | null>(null)
  const firstOptionRef = useRef<HTMLButtonElement | null>(null)
  const lastTriggerUsed = useRef<'icon' | 'text'>('text')

  // Industry dropdown refs
  const industryTriggerRef = useRef<HTMLButtonElement | null>(null)
  
  // Messages scroll ref
  const scrollRef = useRef<HTMLDivElement | null>(null)

  // Activate auto-resize for textarea
  useAutosizeTextarea(textareaRef, inputValue, { minPx: 112, maxVh: 40 })

  // Scroll to bottom helper
  function scrollToBottom(behavior: ScrollBehavior = 'auto') {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  }

  useEffect(() => {
    setIsClient(true)
  }, [])

  // Detect desktop for autoFocus (avoid mobile zoom)
  useEffect(() => {
    const checkDesktop = () => {
      setIsDesktop(window.innerWidth >= 1024)
    }
    checkDesktop()
    window.addEventListener('resize', checkDesktop)
    return () => window.removeEventListener('resize', checkDesktop)
  }, [])

  // Manual focus for desktop (after isDesktop is determined)
  useEffect(() => {
    if (isDesktop && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [isDesktop])

  // Restore focus after assistant finishes typing (desktop only)
  useEffect(() => {
    if (isDesktop && !isAssistantTyping && textareaRef.current) {
      // Small delay to ensure the UI has updated
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus()
        }
      }, 100)
    }
  }, [isAssistantTyping, isDesktop])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollToBottom('smooth');
  }, [messages.length])

  // Handle click outside to close upload menu and role dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isUploadMenuOpen && uploadMenuAnchorRef && !uploadMenuAnchorRef.contains(event.target as Node)) {
        handleUploadMenuClose()
      }
      if (isRoleDropdownOpen) {
        const target = event.target as Node
        // Check if click is inside trigger cluster or dropdown
        if (triggerClusterRef.current?.contains(target)) return
        if (document.getElementById('role-dropdown')?.contains(target)) return
        if (document.getElementById('industry-dropdown')?.contains(target)) return
        closeRoleDropdown()
        closeIndustryDropdown()
        restoreFocusToTrigger(lastTriggerUsed.current)
      }
    }

    if (isUploadMenuOpen || isRoleDropdownOpen || isIndustryDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isUploadMenuOpen, uploadMenuAnchorRef, isRoleDropdownOpen, isIndustryDropdownOpen])

  // Focus first option when opening dropdown
  useEffect(() => {
    if (isRoleDropdownOpen) {
      requestAnimationFrame(() => firstOptionRef.current?.focus())
    }
  }, [isRoleDropdownOpen])

  // Heartbeat check for degraded mode
  useEffect(() => {
    const checkHeartbeat = async () => {
      const result = await fetchTyped('/status', RiskSummarySchema)
      setLastHeartbeat(0) // Mock always fresh
      setIsDegradedMode(false)
    }

    if (isClient) {
      checkHeartbeat()
      const interval = setInterval(checkHeartbeat, 30000) // Check every 30s
      return () => clearInterval(interval)
    }
  }, [isClient])

  // Fetch risk summary data when timeframe changes
  useEffect(() => {
    const fetchRiskSummary = async () => {
      if (!isClient) return
      
      setRiskSummaryLoading(true)
      setRiskSummaryError(null)
      
      const result = await fetchTyped(`/risk/summary?timeframe=${selectedTimeframe}`, RiskSummarySchema)
      
      setRiskSummary(result as RiskSummary)
      setRiskSummaryError(null)
      setIsDegradedMode(false)
      
      setRiskSummaryLoading(false)
    }

    fetchRiskSummary()
  }, [selectedTimeframe, isClient])

  // Helper function to fetch exchange data with proper error handling
  const fetchExchangeData = async (venue: string, url: string) => {
    try {
      const data = await fetchTyped(url, BinanceOverviewSchema)
      const ohlcvLength = (data as any)?.ohlcv?.length ?? 0
      console.log(`✅ [UI Frontend] ${venue} OHLCV length: ${ohlcvLength}`)
      return { venue, ok: true, data }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      console.log(`❌ [UI Frontend] ${venue} fetch failed: ${errorMsg}`)
      return { venue, ok: false, error: errorMsg }
    }
  }

  // Fetch metrics overview data when timeframe changes
  // Fetch all exchange overview data (preview only)
  const fetchExchangeOverview = async () => {
    if (!isClient) return
    
    setExchangeDataLoading(true)
    setExchangeDataError(null)
    
    try {
      console.log(`🔍 [UI Frontend] Starting multi-exchange overview fetch for timeframe: ${selectedTimeframe}...`)
      
      // Fetch all four exchanges in parallel with robust error handling
      const results = await Promise.allSettled([
        fetchExchangeData('binance', `/exchanges/binance/overview?symbol=BTCUSDT&tf=${selectedTimeframe}`),
        fetchExchangeData('okx', `/exchanges/okx/overview?symbol=BTCUSDT&tf=${selectedTimeframe}`),
        fetchExchangeData('bybit', `/exchanges/bybit/overview?symbol=BTCUSDT&tf=${selectedTimeframe}`),
        fetchExchangeData('kraken', `/exchanges/kraken/overview?symbol=BTCUSDT&tf=${selectedTimeframe}`)
      ])
      
      // Extract successful results
      const successfulExchanges = results
        .map(result => result.status === 'fulfilled' ? result.value : null)
        .filter((result): result is { venue: string; ok: true; data: any } => 
          result !== null && result.ok === true
        )
      
      // Log summary
      const successfulVenues = successfulExchanges.map(r => r.venue)
      const barsPerSeries: Record<string, number> = {}
      successfulExchanges.forEach(r => {
        barsPerSeries[r.venue] = (r.data as any)?.ohlcv?.length ?? 0
      })
      
      console.log(`📊 [UI Frontend] Loaded series: [${successfulVenues.join(', ')}]`)
      console.log(`📊 [UI Frontend] Bars per series:`, barsPerSeries)
      
      // Debug logging
      if (process.env.NEXT_PUBLIC_UI_DEBUG === 'true') {
        console.log(`🔍 [UI Frontend] SERIES_SOURCE=live`)
        console.log(`🔍 [UI Frontend] SERIES_VENUES=[${successfulVenues.join(',')}]`)
        console.log(`🔍 [UI Frontend] AVATAR_VENUES=[${successfulVenues.join(',')}]`)
      }
      
      // Create chart series from successful exchanges
      if (successfulExchanges.length > 0) {
        const availableUiVenues: UiVenue[] = getAvailableUiVenues(successfulExchanges)
        const chartData = createChartSeries(successfulExchanges)
        setExchangeData(chartData)
        setAvailableUiVenues(availableUiVenues)
        setExchangeDataError(null)
        console.log(`✅ [UI Frontend] Created chart data with ${chartData.length} points for ${successfulVenues.length} venues`)
        
        // Debug parity
        if (process.env.NEXT_PUBLIC_UI_DEBUG === 'true') {
          console.log('SERIES_VENUES=', availableUiVenues);
        }
      } else {
        // Fallback to demo data if no exchanges available and demo mode is enabled
        if (process.env.NEXT_PUBLIC_DEMO_MODE === 'true') {
          console.log(`🔄 [UI Frontend] No live data available, falling back to demo data`)
          const demoData = getAnalyticsData()
          setExchangeData(demoData)
          setAvailableUiVenues(['binance', 'coinbase', 'bybit', 'kraken'] as UiVenue[])
          setExchangeDataError(null)
          
          if (process.env.NEXT_PUBLIC_UI_DEBUG === 'true') {
            console.log(`🔍 [UI Frontend] SERIES_SOURCE=demo`)
            console.log(`🔍 [UI Frontend] SERIES_VENUES=[binance,coinbase,bybit,kraken]`)
            console.log(`🔍 [UI Frontend] AVATAR_VENUES=[binance,coinbase,bybit,kraken]`)
          }
        } else {
          throw new Error('No exchanges available')
        }
      }
      
    } catch (error) {
      console.error('❌ [UI Frontend] Exchange overview fetch failed:', error)
      setExchangeDataError('Exchange data temporarily unavailable')
      
      // Fallback to demo data if demo mode is enabled
      if (process.env.NEXT_PUBLIC_DEMO_MODE === 'true') {
        console.log(`🔄 [UI Frontend] Error occurred, falling back to demo data`)
        const demoData = getAnalyticsData()
        setExchangeData(demoData)
        setAvailableUiVenues(['binance', 'coinbase', 'bybit', 'kraken'] as UiVenue[])
        setExchangeDataError(null)
      }
    }
    
    setExchangeDataLoading(false)
  }

  useEffect(() => {
    const fetchMetricsOverview = async () => {
      if (!isClient) return
      
      // Always fetch live exchange overviews to populate context + chart
      await fetchExchangeOverview()
      
      // (Optional) If you still need legacy metrics for other widgets,
      // compute them AFTER fetchExchangeOverview() so leadership can use live data.
      // Do NOT return early; let the rest of the effect proceed.
      
      setMetricsLoading(true)
      setMetricsError(null)
      
      const result = await fetchTyped(`/metrics/overview?timeframe=${selectedTimeframe}`, MetricsOverviewSchema)
      
      setMetricsOverview(result as MetricsOverview)
      setMetricsError(null)
      setIsDegradedMode(false)
      
      setMetricsLoading(false)
    }

    fetchMetricsOverview()
  }, [selectedTimeframe, isClient])

  // Fetch health run data
  useEffect(() => {
    const fetchHealthRun = async () => {
      if (!isClient) return
      
      setHealthLoading(true)
      setHealthError(null)
      
      const result = await fetchTyped('/health/run', HealthRunSchema)
      
      setHealthRun(result as HealthRun)
      setHealthError(null)
      setIsDegradedMode(false)
      
      setHealthLoading(false)
    }

    fetchHealthRun()
  }, [isClient])

  // Fetch events data when timeframe changes
  useEffect(() => {
    const fetchEvents = async () => {
      if (!isClient) return
      
      setEventsLoading(true)
      setEventsError(null)
      
      const result = await fetchTyped(`/events?timeframe=${selectedTimeframe}`, EventsResponseSchema)
      
      setEvents(result as EventsResponse)
      setEventsError(null)
      setIsDegradedMode(false)
      
      setEventsLoading(false)
    }

    fetchEvents()
  }, [selectedTimeframe, isClient])

  // Fetch data sources status
  useEffect(() => {
    const fetchDataSources = async () => {
      if (!isClient) return
      
      setDataSourcesLoading(true)
      setDataSourcesError(null)
      
      const result = await fetchTyped('/datasources/status', DataSourcesSchema)
      
      setDataSources(result as DataSources)
      setDataSourcesError(null)
      setIsDegradedMode(false)
      
      setDataSourcesLoading(false)
    }

    fetchDataSources()
  }, [isClient])

  // Close calendar when switching to agents tab and reset sidebar when switching to dashboard
  const handleTabChange = (tab: "agents" | "dashboard") => {
    setActiveTab(tab)
    if (tab === "agents") {
      setIsCalendarOpen(false)
    } else if (tab === "dashboard") {
      setActiveSidebarItem("overview")
    }
  }

  const handleSendMessage = async (customMessage?: string) => {
    const messageContent = customMessage || inputValue.trim()
    if (!messageContent) return

    // Remove focus from input during message sending (desktop only)
    if (isDesktop && textareaRef.current) {
      textareaRef.current.blur()
    }

    // Clear input immediately
    setInputValue("")
    
    // Show typing loader immediately
    setIsAssistantTyping(true)

    // Add user message
    const userMessage = {
      id: Date.now().toString(),
      type: "user" as const,
      content: messageContent,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setHasEngaged(true)
    // once the first message is actually sent, lock this in
    setHasStartedChat(true)
    
    // Scroll to bottom after adding user message
    requestAnimationFrame(() => scrollToBottom('auto'))

    // Check if we should use the API or local mock
    const useApi = process.env.NEXT_PUBLIC_AGENT_CHAT_ENABLED === 'true'
    const streamEnabled = process.env.NEXT_PUBLIC_AGENT_CHAT_STREAM === 'true'

    if (useApi) {
      // Use API route
      try {
        const messagesForApi = [
          ...messages,
          { role: 'user' as const, content: messageContent }
        ]
        
        // Create AbortController for request cancellation
        const abortController = new AbortController()
        let res: Response | null = null
        
        if (streamEnabled) {
          // Streaming mode
          try {
            res = await fetch('/api/agent/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                messages: messagesForApi,
                sessionId: `session_${Date.now()}`
              }),
              signal: abortController.signal,
            })
            
            if (res.headers.get('content-type')?.includes('text/event-stream')) {
              // Handle streaming response
              const reader = res.body?.getReader()
              if (!reader) throw new Error('No reader available')
              
              const decoder = new TextDecoder()
              let buffer = ''
              
              // Create initial agent message
              const agentMessageId = (Date.now() + 1).toString()
              const agentResponse = {
                id: agentMessageId,
                type: "agent" as const,
                content: '',
                timestamp: new Date(),
              }
              setIsAssistantTyping(false) // Hide loader when streaming starts
              setMessages((prev) => [...prev, agentResponse])
              
              // Read streaming chunks
              while (true) {
                const { done, value } = await reader.read()
                if (done) break
                
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''
                
                for (const line of lines) {
                  if (line.trim() === '') continue
                  
                  if (line.startsWith('data: ')) {
                    const data = line.slice(6)
                    if (data === '[DONE]') break
                    
                    try {
                      const parsed = JSON.parse(data)
                      if (parsed.text) {
                        // Append text to existing agent message
                        setMessages((prev) => prev.map(msg => 
                          msg.id === agentMessageId 
                            ? { ...msg, content: msg.content + parsed.text }
                            : msg
                        ))
                      }
                    } catch (e) {
                      // Ignore malformed JSON
                    }
                  }
                }
              }
              return // Exit early if streaming succeeded
            } else {
              // Fallback to non-streaming if response is not streamed
              const data = await res.json()
              
              // Check if this is an error response
              if (data.error) {
                const agentResponse = {
                  id: (Date.now() + 1).toString(),
                  type: "agent" as const,
                  content: `I encountered an error: ${data.error}. Please try again.`,
                  timestamp: new Date(),
                }
                setIsAssistantTyping(false) // Hide loader
                setMessages((prev) => [...prev, agentResponse])
              } else {
                const agentResponse = {
                  id: (Date.now() + 1).toString(),
                  type: "agent" as const,
                  content: data.reply,
                  timestamp: new Date(),
                }
                setIsAssistantTyping(false) // Hide loader
                setMessages((prev) => [...prev, agentResponse])
              }
              return // Exit early if non-streaming fallback succeeded
            }
          } catch (streamError) {
            console.error('Streaming failed, falling back to non-streaming:', streamError)
            // Fall through to non-streaming implementation
          }
        }
        
        // Non-streaming mode (fallback or default)
        if (!streamEnabled || !res) {
          res = await fetch('/api/agent/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              messages: messagesForApi,
              sessionId: `session_${Date.now()}`
            }),
            signal: abortController.signal,
          })
          
          const data = await res.json()
          
          // Check if this is an error response
          if (data.error) {
            const agentResponse = {
              id: (Date.now() + 1).toString(),
              type: "agent" as const,
              content: `I encountered an error: ${data.error}. Please try again.`,
              timestamp: new Date(),
            }
            setIsAssistantTyping(false) // Hide loader
            setMessages((prev) => [...prev, agentResponse])
          } else {
            const agentResponse = {
              id: (Date.now() + 1).toString(),
              type: "agent" as const,
              content: data.reply,
              timestamp: new Date(),
            }
            setIsAssistantTyping(false) // Hide loader
            setMessages((prev) => [...prev, agentResponse])
          }
        }
      } catch (error) {
        console.error('API call failed:', error)
        // Fallback to mock response on API error
        const agentResponse = {
          id: (Date.now() + 1).toString(),
          type: "agent" as const,
          content: `I apologize, but I'm experiencing technical difficulties. Please try again in a moment.`,
          timestamp: new Date(),
        }
        setIsAssistantTyping(false) // Hide loader
        setMessages((prev) => [...prev, agentResponse])
      }
    } else {
      // Use local mock (original behavior)
    setTimeout(() => {
      let agentResponseContent = ""

      if (messageContent === "Help me log a market event") {
        agentResponseContent = `Sounds good, I'll help you log a market event for analysis. I need to understand what happened and its potential implications. Don't worry if you don't have all the details - we can work through this together. What caught your attention that made you want to log this event?

It would also be helpful if you described:
• What market behavior did you observe?
• When did this occur?
• Which companies or participants were involved?`
      } else {
        agentResponseContent = `Thank you for your message: "${messageContent}". I'm your AI economist assistant and I'm here to help you analyze market data, check compliance, and generate reports. How can I assist you today?`
      }

      const agentResponse = {
        id: (Date.now() + 1).toString(),
        type: "agent" as const,
        content: agentResponseContent,
        timestamp: new Date(),
      }
        setIsAssistantTyping(false) // Hide loader
      setMessages((prev) => [...prev, agentResponse])
    }, 1000)
    }
  }

  // Helper function to copy message content to clipboard
  const handleCopy = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
    }
  }

  // Helper function to regenerate assistant response
  const handleRegenerate = async (messageIndex: number) => {
    // Show typing loader immediately
    setIsAssistantTyping(true)

    try {
      // Remove the current assistant message at the specified index
      setMessages((prev) => prev.filter((_, idx) => idx !== messageIndex))

      // Get all messages up to the point where we want to regenerate
      const messagesUpToIndex = messages.slice(0, messageIndex)
      
      // Find the last user message to use as the query
      const lastUserMessage = messagesUpToIndex.reverse().find(msg => msg.type === "user")
      
      if (!lastUserMessage) {
        console.error('No user message found for regeneration')
        setIsAssistantTyping(false)
        return
      }

      // Check if we should use the API or local mock
      if (process.env.NEXT_PUBLIC_AGENT_CHAT_ENABLED === 'true') {
        const streamEnabled = process.env.NEXT_PUBLIC_AGENT_CHAT_STREAM === 'true'
        let res: Response | null = null

        if (streamEnabled) {
          // Streaming mode
          try {
            res = await fetch('/api/agent/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                messages: messagesUpToIndex.map(msg => ({ role: msg.type, content: msg.content })),
                sessionId: `session_${Date.now()}`
              }),
            })

            if (res.ok && res.headers.get('content-type')?.includes('text/event-stream')) {
              const reader = res.body?.getReader()
              if (!reader) throw new Error('No reader available')
              
              const decoder = new TextDecoder()
              let buffer = ''
              
              // Create initial agent message
              const agentMessageId = (Date.now() + 1).toString()
              const agentResponse = {
                id: agentMessageId,
                type: "agent" as const,
                content: '',
                timestamp: new Date(),
              }
              setIsAssistantTyping(false) // Hide loader when streaming starts
              setMessages((prev) => [...prev, agentResponse])
              
              // Read streaming chunks
              while (true) {
                const { done, value } = await reader.read()
                if (done) break
                
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''
                
                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = line.slice(6)
                    if (data === '[DONE]') continue
                    
                    try {
                      const parsed = JSON.parse(data)
                      if (parsed.text) {
                        // Append text to existing agent message
                        setMessages((prev) => prev.map(msg => 
                          msg.id === agentMessageId 
                            ? { ...msg, content: msg.content + parsed.text }
                            : msg
                        ))
                      }
                    } catch (e) {
                      // Ignore parsing errors for malformed chunks
                    }
                  }
                }
              }
              return // Exit early if streaming succeeded
            } else {
              // Fallback to non-streaming if response is not streamed
              const data = await res.json()
              
              // Check if this is an error response
              if (data.error) {
                const agentResponse = {
                  id: (Date.now() + 1).toString(),
                  type: "agent" as const,
                  content: `I encountered an error: ${data.error}. Please try again.`,
                  timestamp: new Date(),
                }
                setIsAssistantTyping(false) // Hide loader
                setMessages((prev) => [...prev, agentResponse])
              } else {
                const agentResponse = {
                  id: (Date.now() + 1).toString(),
                  type: "agent" as const,
                  content: data.reply,
                  timestamp: new Date(),
                }
                setIsAssistantTyping(false) // Hide loader
                setMessages((prev) => [...prev, agentResponse])
              }
              return // Exit early if non-streaming fallback succeeded
            }
          } catch (streamError) {
            console.error('Streaming failed, falling back to non-streaming:', streamError)
            // Fall through to non-streaming implementation
          }
        }
        
        // Non-streaming mode (fallback or default)
        if (!streamEnabled || !res) {
          res = await fetch('/api/agent/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              messages: messagesUpToIndex.map(msg => ({ role: msg.type, content: msg.content })),
              sessionId: `session_${Date.now()}`
            }),
          })
          
          const data = await res.json()
          
          // Check if this is an error response
          if (data.error) {
            const agentResponse = {
              id: (Date.now() + 1).toString(),
              type: "agent" as const,
              content: `I encountered an error: ${data.error}. Please try again.`,
              timestamp: new Date(),
            }
            setIsAssistantTyping(false) // Hide loader
            setMessages((prev) => [...prev, agentResponse])
          } else {
            const agentResponse = {
              id: (Date.now() + 1).toString(),
              type: "agent" as const,
              content: data.reply,
              timestamp: new Date(),
            }
            setIsAssistantTyping(false) // Hide loader
            setMessages((prev) => [...prev, agentResponse])
          }
        }
      } else {
        // Use local mock (original behavior)
        setTimeout(() => {
          let agentResponseContent = ""

          if (lastUserMessage.content === "Help me log a market event") {
            agentResponseContent = `Sounds good, I'll help you log a market event for analysis. I need to understand what happened and its potential implications. Don't worry if you don't have all the details - we can work through this together. What caught your attention that made you want to log this event?

It would also be helpful if you described:
• What market behavior did you observe?
• When did this occur?
• Which companies or participants were involved?`
          } else {
            agentResponseContent = `Thank you for your message: "${lastUserMessage.content}". I'm your AI economist assistant and I'm here to help you analyze market data, check compliance, and generate reports. How can I assist you today?`
          }

          const agentResponse = {
            id: (Date.now() + 1).toString(),
            type: "agent" as const,
            content: agentResponseContent,
            timestamp: new Date(),
          }
          setIsAssistantTyping(false) // Hide loader
          setMessages((prev) => [...prev, agentResponse])
        }, 1000)
      }
    } catch (error) {
      console.error('Regeneration failed:', error)
      // Fallback to mock response on API error
      const agentResponse = {
        id: (Date.now() + 1).toString(),
        type: "agent" as const,
        content: `I apologize, but I'm experiencing technical difficulties. Please try again in a moment.`,
        timestamp: new Date(),
      }
      setIsAssistantTyping(false) // Hide loader
      setMessages((prev) => [...prev, agentResponse])
    }
  }

  // Upload menu handlers
  const handleFiles = (files: FileList) => {
    console.info('Files selected:', Array.from(files).map(f => ({ name: f.name, size: f.size, type: f.type })))
    // TODO: Wire real file ingestion later
  }

  const handleUploadMenuToggle = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setUploadMenuAnchorRef(event.currentTarget)
    setIsUploadMenuOpen(!isUploadMenuOpen)
    setUploadMenuFocusIndex(-1)
  }

  const handleUploadMenuClose = () => {
    setIsUploadMenuOpen(false)
    setUploadMenuFocusIndex(-1)
    uploadMenuAnchorRef?.focus()
  }

  const handleUploadMenuKeyDown = (event: React.KeyboardEvent) => {
    if (!isUploadMenuOpen) return

    switch (event.key) {
      case 'Escape':
        handleUploadMenuClose()
        break
      case 'ArrowDown':
        event.preventDefault()
        setUploadMenuFocusIndex(prev => (prev + 1) % 4)
        break
      case 'ArrowUp':
        event.preventDefault()
        setUploadMenuFocusIndex(prev => (prev - 1 + 4) % 4)
        break
      case 'Enter':
        event.preventDefault()
        if (uploadMenuFocusIndex >= 0) {
          handleUploadAction(uploadMenuFocusIndex)
        }
        break
    }
  }

  const handleUploadAction = (index: number) => {
    const actions = ['photoLibrary', 'takePhoto', 'chooseFiles', 'linkGitHub']
    const action = actions[index]
    
    switch (action) {
      case 'photoLibrary':
        document.getElementById('photo-library-input')?.click()
        break
      case 'takePhoto':
        document.getElementById('camera-input')?.click()
        break
      case 'chooseFiles':
        document.getElementById('file-input')?.click()
        break
      case 'linkGitHub':
        setIsGitHubModalOpen(true)
        break
    }
    handleUploadMenuClose()
  }

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>, type: string) => {
    if (event.target.files) {
      console.info(`${type} files selected:`, Array.from(event.target.files).map(f => ({ name: f.name, size: f.size, type: f.type })))
      handleFiles(event.target.files)
    }
  }

  const handleGitHubConnect = () => {
    console.info({ repoUrl: gitHubRepoUrl })
    setGitHubRepoUrl("")
    setIsGitHubModalOpen(false)
  }

  // Role dropdown handlers
  const handleRoleDropdownToggle = () => {
    setIsRoleDropdownOpen(!isRoleDropdownOpen)
    setRoleDropdownFocusIndex(-1)
  }

  // Dual-trigger dropdown functions
  const openRoleDropdown = () => setIsRoleDropdownOpen(true)
  const closeRoleDropdown = () => setIsRoleDropdownOpen(false)
  
  const restoreFocusToTrigger = (lastTrigger: 'icon' | 'text') => {
    // Both default and chat views now use unified button with triggerIconRef
    triggerIconRef.current?.focus()
  }

  const handleRoleDropdownClose = () => {
    setIsRoleDropdownOpen(false)
    setRoleDropdownFocusIndex(-1)
  }

  const handleRoleSelect = (role: string) => {
    setSelectedAgent(role)
    handleRoleDropdownClose()
  }

  // Industry dropdown functions
  const openIndustryDropdown = () => setIsIndustryDropdownOpen(true)
  const closeIndustryDropdown = () => setIsIndustryDropdownOpen(false)
  
  const handleIndustrySelect = (industry: string) => {
    setSelectedIndustry(industry)
    setIsIndustryDropdownOpen(false)
    setIndustryDropdownFocusIndex(-1)
  }

  const handleRoleDropdownKeyDown = (event: React.KeyboardEvent) => {
    if (!isRoleDropdownOpen) return

    const roles = ["Europe", "South Africa", "United States", "Australia"]

    switch (event.key) {
      case 'Escape':
        handleRoleDropdownClose()
        break
      case 'ArrowDown':
        event.preventDefault()
        setRoleDropdownFocusIndex(prev => (prev + 1) % roles.length)
        break
      case 'ArrowUp':
        event.preventDefault()
        setRoleDropdownFocusIndex(prev => (prev - 1 + roles.length) % roles.length)
        break
      case 'Enter':
        event.preventDefault()
        if (roleDropdownFocusIndex >= 0) {
          handleRoleSelect(roles[roleDropdownFocusIndex])
        }
        break
    }
  }

  // Dual-trigger keyboard handler
  const onTriggerKeyDown: React.KeyboardEventHandler<HTMLButtonElement> = (e) => {
    if (e.key === 'Enter' || e.key === ' ') { 
      e.preventDefault(); 
      openRoleDropdown(); 
    }
    if (e.key === 'ArrowDown') { 
      e.preventDefault(); 
      openRoleDropdown(); 
    }
  }

  // Get the appropriate data based on selected timeframe
  const getAnalyticsData = () => {
    switch (selectedTimeframe) {
      case "30d":
        return analyticsData30d
      case "6m":
        return analyticsData6m
      case "1y":
        return analyticsData1y
      case "ytd":
        return analyticsDataYTD
      default:
        return analyticsDataYTD
    }
  }

  // Render shell tiles for navigation pages
  const renderShellTiles = (pageTitle: string) => {
    return (
      <div className="space-y-3 max-w-2xl">
        {/* First shell tile with left and right containers */}
        <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
          <CardContent className="p-4">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div className="rounded-lg bg-bg-tile shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                <div>
                  <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Left Container</h2>
                  <p className="text-xs text-[#a1a1aa] mb-3 leading-relaxed">
                    Shell content for {pageTitle} - Left side
                  </p>
                </div>
                <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-bg-tile text-[#a1a1aa] hover:text-[#f9fafb] self-start">
                  Action Button
                </button>
              </div>
              <div className="rounded-lg bg-bg-tile2 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                <div>
                  <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Right Container</h2>
                  <p className="text-xs text-[#a1a1aa] mb-3 leading-relaxed">
                    Shell content for {pageTitle} - Right side
                  </p>
                </div>
                <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-bg-tile text-[#a1a1aa] hover:text-[#f9fafb] self-start">
                  Action Button
                </button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Second shell tile */}
        <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
          <CardContent className="p-4 text-center">
            <h3 className="text-[#f9fafb] font-medium mb-1.5 text-xs">Second Shell Tile</h3>
            <p className="text-[10px] text-[#a1a1aa] mb-2.5">Additional shell content for {pageTitle} page.</p>
            <Button
              variant="outline"
              className="border-blue-300 text-[#ffffff] bg-blue-300 hover:bg-blue-400 text-[9px] h-5 px-2 font-normal"
            >
              Shell Action
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Use live exchange data if available, otherwise fall back to static data
  const currentData = exchangeData.length > 0 ? exchangeData : getAnalyticsData()

  // Price leadership calculation
  const keyByVenue: Record<string, DataKey> = {
    binance: 'fnb',
    coinbase: 'absa',
    bybit: 'nedbank',
    kraken: 'standard',
  };

  const activeKeys = (availableUiVenues ?? [])
    .map(v => keyByVenue[v])
    .filter(Boolean) as DataKey[];

  const leadership = computePriceLeadership(currentData, activeKeys);

  // Render the metric (fallback when <2 venues or no signal)
  const leadershipPctText = leadership.pct == null
    ? 'N/A'
    : Math.round(leadership.pct).toString();

  const leadershipCaption = leadership.pct == null
    ? 'Requires multiple venues'
    : `Leader: ${leadership.leader}`;

  // Debug logging for leadership calculation
  if (process.env.NEXT_PUBLIC_UI_DEBUG === 'true') {
    console.log('LEADERSHIP_INPUT_KEYS=', activeKeys);
    console.log('LEADERSHIP_RESULT=', leadership);
  }

  return (
    <div className="min-h-screen bg-[#0f0f10] text-[#f9fafb] font-sans p-4">
      {/* Hidden file inputs for upload menu */}
      <input
        id="photo-library-input"
        type="file"
        accept="image/*"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => handleFileInputChange(e, 'Photo Library')}
      />
      <input
        id="camera-input"
        type="file"
        accept="image/*,video/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(e) => handleFileInputChange(e, 'Camera')}
      />
      <input
        id="file-input"
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => handleFileInputChange(e, 'Files')}
      />
      {/* Header */}
      <header className="border-b border-[#1a1a1a] px-5 py-1.5 relative">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-shrink-0">
            <button 
              onClick={() => window.location.reload()}
              className="cursor-pointer focus:outline-none"
              aria-label="Refresh page"
            >
              <img 
                src="/ninja-glow-positive.png" 
                alt="Ninja Glow" 
                className="h-14 sm:h-16 md:h-24 w-auto opacity-90 hover:opacity-100 transition-opacity -ml-3 sm:ml-0 flex-shrink-0 object-contain"
              />
            </button>
          </div>

          <nav className="flex gap-4 sm:gap-5 absolute left-1/2 transform -translate-x-1/2">
            <button
              onClick={() => handleTabChange("agents")}
              className={`px-2.5 py-1 text-xs font-medium ${
                activeTab === "agents" ? "text-[#f9fafb]" : "text-[#a1a1aa] hover:text-[#f9fafb]"
              }`}
            >
              Agents
            </button>
            <button
              onClick={() => handleTabChange("dashboard")}
              className={`px-2.5 py-1 text-xs font-medium ${
                activeTab === "dashboard" ? "text-[#f9fafb]" : "text-[#a1a1aa] hover:text-[#f9fafb]"
              }`}
            >
              Diagnostic
            </button>
          </nav>

          <div className="text-xs font-medium text-[#f9fafb] bg-bg-tile rounded-full w-7 h-7 flex items-center justify-center">
            YF
          </div>
        </div>
      </header>

      {/* Degraded Mode Banner */}
      <DegradedModeBanner isVisible={isDegradedMode} lastHeartbeat={lastHeartbeat || undefined} />

      {/* Extra spacing below header */}
      <div className="h-6"></div>

      <div className="flex justify-center">
        <div className={`max-w-5xl w-full ${activeTab === "dashboard" ? "grid grid-cols-1 gap-6 lg:grid-cols-[18rem_1fr] lg:gap-8 px-4 sm:px-6 lg:px-8" : "flex"}`} data-root-grid={activeTab === "dashboard" ? "dash" : undefined}>
          {/* Sidebar - Only show on dashboard */}
          {activeTab === "dashboard" && (
            <aside className="lg:sticky lg:top-16 lg:h-[calc(100dvh-4rem)] bg-[#0f0f10] p-3">
              <div className="space-y-3">
                {/* User Info */}
                <div>
                  <h3 className="text-xs font-semibold text-[#f9fafb] mb-1">Ygor Francisco</h3>
                  <p className="text-[10px] text-[#a1a1aa] mb-2.5">Ent Plan · ygor.francisco@gmail.com</p>

                  <div
                    className={`rounded-md p-1.5 mb-2.5 cursor-pointer ${activeSidebarItem === "overview" ? "bg-bg-tile" : "hover:bg-bg-tile"}`}
                    onClick={() => setActiveSidebarItem("overview")}
                  >
                    <div className="flex items-center gap-2 text-xs font-medium text-[#f9fafb]">
                      <User className="w-3.5 h-3.5" />
                      Overview
                    </div>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div
                      className={`flex items-center gap-2 px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "configuration" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}
                      onClick={() => setActiveSidebarItem("configuration")}
                    >
                      <Settings className="w-3.5 h-3.5" />
                      Settings
                    </div>
                  </div>
                </div>

                <Separator className="bg-bg-tile" />

                {/* Navigation */}
                <nav className="space-y-0.5">
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "data-sources" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}
                    onClick={() => setActiveSidebarItem("data-sources")}
                  >
                    <Database className="w-3.5 h-3.5" />
                    Data
                  </div>
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "ai-economists" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}
                    onClick={() => setActiveSidebarItem("ai-economists")}
                  >
                    <Bot className="w-3.5 h-3.5" />
                    Analysts
                  </div>
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "health-checks" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}
                    onClick={() => setActiveSidebarItem("health-checks")}
                  >
                    <Zap className="w-3.5 h-3.5" />
                    Health
                  </div>
                </nav>

                <Separator className="bg-bg-tile" />

                <nav className="space-y-0.5">
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "events-log" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}
                    onClick={() => setActiveSidebarItem("events-log")}
                  >
                    <ClipboardList className="w-3.5 h-3.5" />
                    Events
                  </div>
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "billing" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}
                    onClick={() => setActiveSidebarItem("billing")}
                  >
                    <CreditCard className="w-3.5 h-3.5" />
                    Billing
                  </div>
                </nav>

                <Separator className="bg-bg-tile" />

                <nav className="space-y-0.5">
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "compliance" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}
                    onClick={() => setActiveSidebarItem("compliance")}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    Reports
                  </div>
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "contact" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}
                    onClick={() => setActiveSidebarItem("contact")}
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    Contact
                  </div>
                </nav>
              </div>
            </aside>
          )}

          {/* Main Content */}
          <main className={`${activeTab === "dashboard" ? "min-w-0 p-5" : `flex-1 ${messages.length === 0 ? "pt-12" : "pt-6"} px-5 pb-5 max-w-5xl mx-auto`}`}>
            {activeTab === "agents" && (
              <div className="max-w-5xl mx-auto">
                {/* <CHANGE> Added main headline for Agents tab - only show when no messages */}
                {messages.length === 0 && (
                  <div className="text-center mb-12 mt-8">
                    <h1 className="font-headline text-6xl md:text-6xl lg:text-7xl text-blue-50 font-light leading-tight max-w-4xl mx-auto">
                      Algorithmic Collusion? Detectable.
                    </h1>
                  </div>
                )}
                {/* Initial Agent Message */}
                {initialAgentMessage && (
                  <div className="mb-4 p-3 bg-bg-surface rounded-lg border border-[#2a2a2a]">
                    <div className="flex items-center gap-2 mb-2">
                      <Bot className="w-4 h-4 text-[#86a789]" />
                      <span className="text-xs font-medium text-[#f9fafb]">{selectedAgent}</span>
                    </div>
                    <AssistantBubble text={initialAgentMessage} />
                  </div>
                )}

              {/* Chat Interface */}
              <div className={`${hasEngaged ? "h-[calc(75vh+16px)]" : "min-h-[calc(50vh+16px)]"} flex flex-col mt-2`}>
                  {/* Chat Messages Area */}
                  {hasEngaged && (
                    <div
                      ref={scrollRef}
                      className="flex-1 overflow-y-auto mb-4 space-y-4 messages-container pb-32 pt-6 chat-messages-container"
                    >
                      {messages.map((message, index) => (
                        <div key={message.id} className="w-full">
                          {message.type === "agent" ? (
                            <div className="flex items-start gap-3">
                              <div className="h-24 w-24 rounded-full flex items-center justify-center overflow-hidden bg-transparent mt-1 flex-shrink-0">
                                <Image
                                  src="/icons/icon-americas.png"
                                  alt="Agent"
                                  width={96}
                                  height={96}
                                  className="h-18 w-18 object-contain"
                                />
                              </div>
                              <div className="flex-1">
                                <AssistantBubble text={message.content} />
                                {/* Control icons for assistant messages (left-aligned) */}
                                <div className="flex gap-2 mt-1 text-gray-400 hover:text-gray-600 cursor-pointer justify-start">
                                  <Copy 
                                    className="w-3 h-3 lg:w-4 lg:h-4 hover:text-[#86a789]" 
                                    onClick={() => handleCopy(message.content)}
                                    aria-label="Copy"
                                  />
                                  <RefreshCw 
                                    className="w-3 h-3 lg:w-4 lg:h-4 hover:text-[#86a789]" 
                                    onClick={() => handleRegenerate(index)}
                                    aria-label="Regenerate"
                                  />
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="flex justify-end">
                              <div className="max-w-[60%] bg-[#2a2a2a] rounded-lg px-6 py-4 text-xs lg:text-base lg:leading-5 text-[#f9fafb]">
                                {message.content}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                      {/* Typing Loader */}
                      {isAssistantTyping && (
                        <div className="w-full">
                          <div className="flex items-start gap-3">
                            <div className="h-24 w-24 rounded-full flex items-center justify-center overflow-hidden bg-transparent mt-1 flex-shrink-0">
                              <Image
                                src="/icons/icon-americas.png"
                                alt="Agent"
                                width={96}
                                height={96}
                                className="h-18 w-18 object-contain animate-scalePulse"
                              />
                            </div>
                            <div className="flex-1 text-xs lg:text-base lg:leading-5 text-[#f9fafb] leading-relaxed">
                              <div className="flex items-center gap-2">
                                <div className="inline-block w-2 h-2 bg-white rounded-full animate-pulse"></div>
                                <span className="text-gray-400 opacity-70">Thinking...</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Input Area */}
                  {!hasEngaged && (
                    <div className={`composer ${chatStarted ? 'composer--tight' : ''} flex flex-col items-center justify-center space-y-5`}>
                  <div className="w-full space-y-3 mx-4 sm:mx-0">
                    <div className="agents-no-zoom-wrapper" data-testid="agents-no-zoom-wrapper">
                      <div className="relative">
                      <textarea
                          ref={textareaRef}
                          placeholder="How can I help test your algorithm today?"
                          value={inputValue}
                          onChange={(e) => setInputValue(e.target.value.slice(0, 25000))}
                          autoFocus={isDesktop}
                          onFocus={() => setIsInputFocused(true)}
                          onBlur={() => {
                            setIsInputFocused(false)
                            // Reset scroll position when keyboard dismisses on mobile
                            if (!isDesktop) {
                              setTimeout(() => {
                                window.scrollTo(0, 0)
                              }, 100)
                            }
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                              e.preventDefault()
                              handleSendMessage()
                            }
                          }}
                          className="w-full bg-bg-tile rounded-lg text-[#f9fafb]
                            px-4 pt-4 pb-16 md:pb-[76px] pr-16
                            text-xs md:text-base leading-5
                            placeholder:text-xs md:placeholder:text-base placeholder:text-[#71717a]
                            whitespace-pre-wrap break-words
                            resize-none overflow-y-hidden focus:outline-none
                            shadow-[0_1px_0_rgba(0,0,0,0.20)] border border-[#2a2a2a]/50
                            min-h-[112px] max-h-[40vh]"
                          style={{ caretColor: "rgba(249, 250, 251, 0.8)" }}
                          rows={1}
                        />
                        {/* Blinking cursor overlay - only shows when empty, on mobile, and not focused */}
                        {inputValue === "" && !isDesktop && !isInputFocused && (
                          <span
                            aria-hidden
                            className="pointer-events-none absolute left-4 top-4 h-[1em] md:h-[1.2em] w-[1px] md:w-[2px] bg-white animate-[blink_1s_steps(1)_infinite]"
                          />
                        )}
                        {/* Model selector - bottom left */}
                        <div ref={triggerClusterRef} className="absolute left-3 bottom-3 flex items-center gap-1.5">
                          {/* UNIFIED GLOBE + TEXT BUTTON */}
                          <button
                            ref={triggerIconRef}
                            type="button"
                            onClick={(e) => { e.stopPropagation(); lastTriggerUsed.current = 'icon'; openRoleDropdown(); }}
                            onKeyDown={onTriggerKeyDown}
                            aria-haspopup="listbox"
                            aria-controls="role-dropdown"
                            aria-expanded={isRoleDropdownOpen}
                            aria-label="Select analysis mode"
                            className="flex items-center gap-1.5 p-1.5 rounded-md bg-transparent border border-[#2a2a2a] hover:border-[#3a3a3a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#60a5fa] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f0f10]"
                          >
                            <Image
                              src="/icons/icon-americas.png"
                              alt="Select analysis mode"
                              width={18}
                              height={18}
                              draggable={false}
                              className="shrink-0"
                            />
                            <span className="text-xs text-[#71717a] font-medium">
                              {getRegionAcronym(selectedAgent)}
                            </span>
                            <ChevronDown className="w-3 h-3 text-[#71717a]" aria-hidden="true" />
                          </button>

                          {/* INDUSTRY BUTTON */}
                          <button
                            ref={industryTriggerRef}
                            type="button"
                            onClick={(e) => { e.stopPropagation(); openIndustryDropdown(); }}
                            aria-haspopup="listbox"
                            aria-controls="industry-dropdown"
                            aria-expanded={isIndustryDropdownOpen}
                            aria-label="Select industry"
                            className="flex items-center gap-1.5 p-1.5 rounded-md bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#60a5fa] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f0f10]"
                          >
                            <Factory className="w-4 h-4 text-[#71717a]" />
                            <span className="text-[10px] text-[#71717a] font-medium">
                              {getIndustryAcronym(selectedIndustry)}
                            </span>
                            <ChevronDown className="w-3 h-3 text-[#71717a]" aria-hidden="true" />
                          </button>
                        </div>

                        {/* Role Dropdown Menu */}
                        {isRoleDropdownOpen && (
                          <div
                            id="role-dropdown"
                            className="absolute z-50 left-3 top-12 w-40 rounded-md border border-white/10 bg-neutral-900/90 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-neutral-900/80"
                            role="listbox"
                            aria-label="Analysis mode"
                            aria-orientation="vertical"
                          >
                            <div className="py-1">
                              {["Europe", "South Africa", "United States", "Australia"].map((role, index) => (
                                <button
                                  key={role}
                                  ref={index === 0 ? firstOptionRef : null}
                                  className={`flex items-center gap-2 px-3 py-2 text-sm text-gray-200 hover:text-white hover:bg-white/5 w-full text-left ${
                                    roleDropdownFocusIndex === index ? 'bg-white/5 text-white' : ''
                                  } ${selectedAgent === role ? 'bg-white/5' : ''}`}
                                  onClick={() => {
                                    setSelectedAgent(role)
                                    closeRoleDropdown()
                                    restoreFocusToTrigger(lastTriggerUsed.current)
                                  }}
                                  role="option"
                                  aria-selected={selectedAgent === role}
                                >
                                  {role}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Industry Dropdown Menu */}
                        {isIndustryDropdownOpen && (
                          <div
                            id="industry-dropdown"
                            role="listbox"
                            aria-label="Select industry"
                            className="absolute z-50 left-3 top-12 w-40 rounded-md border border-white/10 bg-neutral-900/90 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-neutral-900/80"
                            aria-orientation="vertical"
                          >
                            <div className="py-1">
                              {["Crypto", "Travel & Hospitality", "E-commerce", "Shipping & Logistics", "Media & Advertising", "Real-Estate", "Telecommunications", "Financial services"].map((industry, index) => (
                                <button
                                  key={industry}
                                  className={`flex items-center gap-2 px-3 py-2 text-sm text-gray-200 hover:text-white hover:bg-white/5 w-full text-left ${
                                    industryDropdownFocusIndex === index ? 'bg-white/5 text-white' : ''
                                  } ${selectedIndustry === industry ? 'bg-white/5' : ''}`}
                                  onClick={() => {
                                    setSelectedIndustry(industry)
                                    closeIndustryDropdown()
                                  }}
                                  role="option"
                                  aria-selected={selectedIndustry === industry}
                                >
                                  {industry}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Action buttons - bottom right */}
                        <div className="absolute right-3 bottom-3 flex gap-1.5">
                          <div className="relative">
                            <button
                              ref={setUploadMenuAnchorRef}
                            className="h-6 w-6 flex items-center justify-center cursor-pointer mr-3"
                              onClick={handleUploadMenuToggle}
                              onKeyDown={handleUploadMenuKeyDown}
                              aria-haspopup="menu"
                              aria-expanded={isUploadMenuOpen}
                              aria-label="Upload options"
                          >
                            <CloudUpload className="w-4 h-4 text-[#71717a] hover:text-[#a1a1aa]" />
                            </button>
                            
                            {/* Upload Menu Popover */}
                            {isUploadMenuOpen && (
                              <div
                                className="absolute right-0 top-full mt-2 z-50 origin-top-right w-[min(280px,calc(100vw-24px))] sm:w-56 max-w-[calc(100vw-24px)] max-h-[60vh] overflow-y-auto rounded-md border border-zinc-800 bg-zinc-900/95 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-zinc-900/80"
                                role="menu"
                                aria-orientation="vertical"
                              >
                                <div className="py-1">
                                  <button
                                    className={`flex items-center gap-3 px-3 h-8 text-sm text-zinc-300 hover:text-[#a1a1aa] hover:bg-zinc-800 rounded cursor-pointer w-full text-left ${
                                      uploadMenuFocusIndex === 0 ? 'bg-zinc-800 text-[#a1a1aa]' : ''
                                    }`}
                                    onClick={() => handleUploadAction(0)}
                                    role="menuitem"
                                  >
                                    <ImageUp className="w-4 h-4" />
                                    Photo Library
                                  </button>
                                  <button
                                    className={`flex items-center gap-3 px-3 h-8 text-sm text-zinc-300 hover:text-[#a1a1aa] hover:bg-zinc-800 rounded cursor-pointer w-full text-left ${
                                      uploadMenuFocusIndex === 1 ? 'bg-zinc-800 text-[#a1a1aa]' : ''
                                    }`}
                                    onClick={() => handleUploadAction(1)}
                                    role="menuitem"
                                  >
                                    <Camera className="w-4 h-4" />
                                    Take Photo or Video
                                  </button>
                                  <button
                                    className={`flex items-center gap-3 px-3 h-8 text-sm text-zinc-300 hover:text-[#a1a1aa] hover:bg-zinc-800 rounded cursor-pointer w-full text-left ${
                                      uploadMenuFocusIndex === 2 ? 'bg-zinc-800 text-[#a1a1aa]' : ''
                                    }`}
                                    onClick={() => handleUploadAction(2)}
                                    role="menuitem"
                                  >
                                    <FolderClosed className="w-4 h-4" />
                                    Choose Files
                                  </button>
                                  <button
                                    className={`flex items-center gap-3 px-3 h-8 text-sm text-zinc-300 hover:text-[#a1a1aa] hover:bg-zinc-800 rounded cursor-pointer w-full text-left ${
                                      uploadMenuFocusIndex === 3 ? 'bg-zinc-800 text-[#a1a1aa]' : ''
                                    }`}
                                    onClick={() => handleUploadAction(3)}
                                    role="menuitem"
                                  >
                                    <Github className="w-4 h-4" />
                                    Link GitHub
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                          <button
                            type="button"
                            aria-label="Send"
                            className="
                              h-6 w-6 flex items-center justify-center cursor-pointer
                              text-[#f9fafb]
                              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#60a5fa]
                              focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f0f10]
                              disabled:text-[#a1a1aa]/50
                              transition-colors motion-reduce:transition-none
                            "
                            onClick={(e) => {
                              e.preventDefault();
                              handleSendMessage();
                            }}
                          >
                            <Send 
                              className="w-6 h-6 opacity-85 hover:opacity-100 text-current transition-opacity duration-200"
                              stroke="currentColor"
                            />
                          </button>
                        </div>
                      </div>
                    </div>

                      {/* Quick Action Buttons - only show when not engaged */}
                      {!hasEngaged && (
                        <div className="space-y-4 mt-6">
                      <p className="text-[10px] text-[#a1a1aa] text-center">Try these examples to get started</p>

                          <div className="flex flex-wrap gap-2 justify-center max-w-4xl mx-auto sm:flex-nowrap">
                            <button 
                              type="button"
                              className="agents-quick-btn"
                            >
                              <Search className="w-2 h-2 md:w-2.5 md:h-2.5" />
                              Audit my algorithm
                            </button>
                            <button 
                              type="button"
                              className="agents-quick-btn"
                            >
                              <BarChart3 className="w-2 h-2 md:w-2.5 md:h-2.5" />
                              Calculate damages
                            </button>
                            <button 
                              type="button"
                              className="agents-quick-btn"
                            >
                              <Scale className="w-2 h-2 md:w-2.5 md:h-2.5" />
                              Compliance risks
                            </button>
                            <button 
                              type="button"
                              className="agents-quick-btn"
                            >
                              <ClipboardList className="w-2 h-2 md:w-2.5 md:h-2.5" />
                              Evidence bundle
                            </button>
                      </div>
                    </div>
                      )}
                  </div>
                </div>
                  )}
              </div>

              {/* Fixed Input Area for Chat State */}
              {hasEngaged && (
                <div className="fixed bottom-0 left-0 right-0 bg-black md:bg-[#0f0f10] border-t border-[#2a2a2a] z-50 fixed-input-container">
                  <div className="max-w-5xl mx-auto px-5 py-4 pb-8 md:pb-4">
                    <div className="w-full space-y-3">
                      <div className="agents-no-zoom-wrapper" data-testid="agents-no-zoom-wrapper">
                        <div className="relative">
                          <textarea
                            ref={textareaRef}
                            placeholder="How can I help test your algorithm today?"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value.slice(0, 25000))}
                            autoFocus={isDesktop}
                            onFocus={() => setIsInputFocused(true)}
                            onBlur={() => {
                              setIsInputFocused(false)
                              // Reset scroll position when keyboard dismisses on mobile
                              if (!isDesktop) {
                                setTimeout(() => {
                                  window.scrollTo(0, 0)
                                }, 100)
                              }
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault()
                                handleSendMessage()
                              }
                            }}
                            className="w-full bg-bg-tile rounded-lg text-[#f9fafb]
                              px-4 pt-4 pb-16 md:pb-[76px] pr-16
                              text-xs md:text-base leading-5
                              placeholder:text-xs md:placeholder:text-base placeholder:text-[#71717a]
                              whitespace-pre-wrap break-words
                              resize-none overflow-y-hidden focus:outline-none
                              shadow-[0_1px_0_rgba(0,0,0,0.20)] border border-[#2a2a2a]/50
                              min-h-[112px] max-h-[40vh]"
                            style={{ caretColor: "rgba(249, 250, 251, 0.8)" }}
                            rows={1}
                          />
                          {/* Blinking cursor overlay - only shows when empty, on mobile, and not focused */}
                          {inputValue === "" && !isDesktop && !isInputFocused && (
                            <span
                              aria-hidden
                              className="pointer-events-none absolute left-4 top-4 h-[1em] md:h-[1.2em] w-[1px] md:w-[2px] bg-white animate-[blink_1s_steps(1)_infinite]"
                            />
                          )}
                          {/* Model selector - bottom left */}
                          <div ref={triggerClusterRef} className="absolute left-3 bottom-3 flex items-center gap-1.5">
                            {/* UNIFIED GLOBE + TEXT BUTTON */}
                            <button
                              ref={triggerIconRef}
                              type="button"
                              onClick={(e) => { e.stopPropagation(); lastTriggerUsed.current = 'icon'; openRoleDropdown(); }}
                              onKeyDown={onTriggerKeyDown}
                              aria-haspopup="listbox"
                              aria-controls="role-dropdown"
                              aria-expanded={isRoleDropdownOpen}
                              aria-label="Select analysis mode"
                              className="flex items-center gap-1.5 p-1.5 rounded-md bg-transparent border border-[#2a2a2a] hover:border-[#3a3a3a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#60a5fa] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f0f10]"
                            >
                              <Image
                                src="/icons/icon-americas.png"
                                alt="Select analysis mode"
                                width={18}
                                height={18}
                                draggable={false}
                                className="shrink-0"
                              />
                              <span className="text-xs text-[#71717a] font-medium">
                                {getRegionAcronym(selectedAgent)}
                              </span>
                              <ChevronDown className="w-3 h-3 text-[#71717a]" aria-hidden="true" />
                            </button>

                            {/* INDUSTRY BUTTON */}
                            <button
                              ref={industryTriggerRef}
                              type="button"
                              onClick={(e) => { e.stopPropagation(); openIndustryDropdown(); }}
                              aria-haspopup="listbox"
                              aria-controls="industry-dropdown"
                              aria-expanded={isIndustryDropdownOpen}
                              aria-label="Select industry"
                              className="flex items-center gap-1.5 p-1.5 rounded-md bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#60a5fa] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f0f10]"
                            >
                              <Factory className="w-4 h-4 text-[#71717a]" />
                              <span className="text-[10px] text-[#71717a] font-medium">
                                {getIndustryAcronym(selectedIndustry)}
                              </span>
                              <ChevronDown className="w-3 h-3 text-[#71717a]" aria-hidden="true" />
                            </button>

                            {/* Role Dropdown */}
                            {isRoleDropdownOpen && (
                              <div
                                id="role-dropdown"
                                role="listbox"
                                aria-label="Select analysis mode"
                                className="absolute bottom-full mb-2 left-0 min-w-[200px] bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg py-1 z-50"
                              >
                                {["Europe", "South Africa", "United States", "Australia"].map((role, index) => (
                                  <div
                                    key={role}
                                    role="option"
                                    aria-selected={selectedAgent === role}
                                    tabIndex={index === 0 ? 0 : -1}
                                    className={`px-3 py-2 text-sm cursor-pointer ${
                                      roleDropdownFocusIndex === index ? 'bg-zinc-700 text-[#a1a1aa]' : 'text-zinc-300 hover:bg-zinc-700 hover:text-[#a1a1aa]'
                                    }`}
                                    onClick={() => handleRoleSelect(role)}
                                  >
                                    {role}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Industry Dropdown */}
                            {isIndustryDropdownOpen && (
                              <div
                                id="industry-dropdown"
                                role="listbox"
                                aria-label="Select industry"
                                className="absolute bottom-full mb-2 left-0 min-w-[200px] bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg py-1 z-50"
                              >
                                {["Crypto", "Travel & Hospitality", "E-commerce", "Shipping & Logistics", "Media & Advertising", "Real-Estate", "Telecommunications", "Financial services"].map((industry, index) => (
                                  <div
                                    key={industry}
                                    role="option"
                                    aria-selected={selectedIndustry === industry}
                                    tabIndex={index === 0 ? 0 : -1}
                                    className={`px-3 py-2 text-sm cursor-pointer ${
                                      industryDropdownFocusIndex === index ? 'bg-zinc-700 text-[#a1a1aa]' : 'text-zinc-300 hover:bg-zinc-700 hover:text-[#a1a1aa]'
                                    }`}
                                    onClick={() => handleIndustrySelect(industry)}
                                  >
                                    {industry}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Upload Button - bottom right before send */}
                          <div className="absolute right-12 bottom-3 flex items-center gap-1.5">
                            <button
                              type="button"
                              aria-label="Upload files"
                              className="h-6 w-6 flex items-center justify-center cursor-pointer text-[#71717a] hover:text-[#a1a1aa] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#60a5fa] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f0f10] transition-colors motion-reduce:transition-none"
                              onClick={handleUploadMenuToggle}
                            >
                              <CloudUpload className="w-4 h-4" />
                            </button>

                            {/* Upload Menu */}
                            {isUploadMenuOpen && (
                              <div className="absolute bottom-full mb-2 right-0 min-w-[180px] bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg py-1 z-50">
                                <button
                                  className={`flex items-center gap-3 px-3 h-8 text-sm text-zinc-300 hover:text-[#a1a1aa] hover:bg-zinc-800 rounded cursor-pointer w-full text-left ${
                                    uploadMenuFocusIndex === 0 ? 'bg-zinc-800 text-[#a1a1aa]' : ''
                                  }`}
                                  onClick={() => handleUploadAction(0)}
                                  role="menuitem"
                                >
                                  <FileText className="w-4 h-4" />
                                  Upload Document
                                </button>
                                <button
                                  className={`flex items-center gap-3 px-3 h-8 text-sm text-zinc-300 hover:text-[#a1a1aa] hover:bg-zinc-800 rounded cursor-pointer w-full text-left ${
                                    uploadMenuFocusIndex === 1 ? 'bg-zinc-800 text-[#a1a1aa]' : ''
                                  }`}
                                  onClick={() => handleUploadAction(1)}
                                  role="menuitem"
                                >
                                  <Camera className="w-4 h-4" />
                                  Take Photo or Video
                                </button>
                                <button
                                  className={`flex items-center gap-3 px-3 h-8 text-sm text-zinc-300 hover:text-[#a1a1aa] hover:bg-zinc-800 rounded cursor-pointer w-full text-left ${
                                    uploadMenuFocusIndex === 2 ? 'bg-zinc-800 text-[#a1a1aa]' : ''
                                  }`}
                                  onClick={() => handleUploadAction(2)}
                                  role="menuitem"
                                >
                                  <FolderClosed className="w-4 h-4" />
                                  Choose Files
                                </button>
                                <button
                                  className={`flex items-center gap-3 px-3 h-8 text-sm text-zinc-300 hover:text-[#a1a1aa] hover:bg-zinc-800 rounded cursor-pointer w-full text-left ${
                                    uploadMenuFocusIndex === 3 ? 'bg-zinc-800 text-[#a1a1aa]' : ''
                                  }`}
                                  onClick={() => handleUploadAction(3)}
                                  role="menuitem"
                                >
                                  <Github className="w-4 h-4" />
                                  Link GitHub
                                </button>
                              </div>
                            )}
                          </div>
                          {/* Send Button - bottom right */}
                          <div className="absolute right-3 bottom-3 flex items-center gap-1.5">
                            <button
                              type="button"
                              aria-label="Send"
                              className="h-6 w-6 flex items-center justify-center cursor-pointer text-[#f9fafb] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#60a5fa] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f0f10] disabled:text-[#a1a1aa]/50 transition-colors motion-reduce:transition-none"
                              onClick={(e) => {
                                e.preventDefault();
                                handleSendMessage();
                              }}
                            >
                              <Send 
                                className="w-6 h-6 opacity-85 hover:opacity-100 text-current transition-opacity duration-200"
                                stroke="currentColor"
                              />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              </div>
            )}
            {activeTab === "dashboard" && (
              /* Dashboard View */
              <>
                {activeSidebarItem === "overview" && (
              <div className="space-y-3 max-w-2xl" data-probe="dash-cards-section">
                <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-4">
                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                          <div className="rounded-lg bg-bg-tile shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                            <div>
                        <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Enterprise Plan</h2>
                              <p className="text-xs text-[#a1a1aa] mb-3 leading-relaxed">
                                Live monitoring with compliance tracking
                        </p>
                            </div>
                            <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-bg-tile text-[#a1a1aa] hover:text-[#f9fafb] self-start">
                          Manage Subscription
                        </button>
                      </div>
                          <div className="rounded-lg bg-bg-tile2 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                            <div>
                          <div className="text-xs font-bold text-[#f9fafb] mb-1">$0 / $6k</div>
                          <p className="text-xs text-[#a1a1aa] mb-2">Usage-Based Spending this Month</p>
                            </div>
                            <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-bg-tile text-[#a1a1aa] hover:text-[#f9fafb] self-start">
                            Edit Limit
                          </button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2 text-xs text-[#a1a1aa]">
                        {isClient && activeTab === "dashboard" && (
                              <>
                          <button 
                            onClick={() => setIsCalendarOpen(!isCalendarOpen)}
                            className="rounded-full px-3 py-1 text-xs border border-[#3a3a3a] bg-transparent hover:bg-[#2a2a2a]/50 text-[#a1a1aa] hover:text-[#f9fafb] flex items-center gap-1"
                          >
                            <CalendarIcon className="h-3 w-3" />
                                  {selectedTimeframe === "30d"
                                    ? "Aug 06 - Sep 10"
                                    : selectedTimeframe === "6m"
                                      ? "Mar '25 - Sep '25"
                                      : selectedTimeframe === "1y"
                                        ? "Sep '24 - Sep '25"
                                        : "Jan 01 - Sep 05"}
                          </button>

                        <div className="flex gap-1">
                          <button 
                            onClick={() => setSelectedTimeframe("30d")}
                                    className={`text-xs px-2 py-1 ${selectedTimeframe === "30d" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                          >
                            30d
                          </button>
                          <button 
                            onClick={() => setSelectedTimeframe("6m")}
                                    className={`text-xs px-2 py-1 ${selectedTimeframe === "6m" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                          >
                            6m
                          </button>
                          <button 
                            onClick={() => setSelectedTimeframe("1y")}
                                    className={`text-xs px-2 py-1 ${selectedTimeframe === "1y" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                          >
                            1y
                          </button>
                          <button 
                            onClick={() => setSelectedTimeframe("ytd")}
                                    className={`text-xs px-2 py-1 ${selectedTimeframe === "ytd" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                          >
                            YTD
                          </button>
                        </div>
                              </>
                      )}
                          </div>
                    </div>

                    <div className="mb-4">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-xs font-medium text-[#f9fafb]">Collusion Risk Score</h3>
                          </div>
                          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 mb-10">
                            <div className="rounded-lg bg-bg-surface shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 relative">
                              {/* Live indicator - pulsing green dot with frame */}
                              <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-bg-tile border border-[#2a2a2a] rounded-full px-2 py-1">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                <span className="text-[10px] text-[#a1a1aa]">LIVE</span>
                              </div>
                          {riskSummaryLoading ? (
                            <div className="animate-pulse">
                              <div className="h-6 bg-[#2a2a2a] rounded w-20 mb-1"></div>
                              <div className="h-3 bg-[#2a2a2a] rounded w-16"></div>
                            </div>
                          ) : riskSummaryError ? (
                            <div className="text-center">
                              <div className="text-sm text-[#fca5a5] mb-1">Error</div>
                              <div className="text-xs text-[#a1a1aa]">Retry</div>
                            </div>
                          ) : riskSummary ? (
                            <>
                              <div className="text-xl font-bold text-[#f9fafb]">{riskSummary.score} out of 100</div>
                              <div className={`text-xs ${
                                riskSummary.band === 'LOW' ? 'text-[#a7f3d0]' :
                                riskSummary.band === 'AMBER' ? 'text-[#fbbf24]' :
                                'text-[#fca5a5]'
                              }`}>
                                {riskSummary.band === 'LOW' ? 'Low Risk' :
                                 riskSummary.band === 'AMBER' ? 'Amber Risk' :
                                 'High Risk'}
                              </div>
                            </>
                          ) : (
                            <>
                          <div className="text-xl font-bold text-[#f9fafb]">14 out of 100</div>
                              <div className="text-xs text-[#a7f3d0]">Low Risk</div>
                            </>
                          )}
                        </div>
                            <div className="rounded-lg bg-bg-surface/40 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                              <div className="flex items-center justify-between">
                        <div>
                                  <div className="text-xl font-bold text-[#f9fafb]">
                                    {leadershipPctText}%
                        </div>
                                  <div className="text-xs text-[#a1a1aa]">
                                    {leadershipCaption}
                                  </div>
                                </div>
                                {/* Venue Avatars (dynamic, in lockstep with series) */}
                                {(() => {
                                  const { availableUiVenues } = useExchangeData();

                                  // optional: gradient opacity for visual hierarchy
                                  const opacities = [1, 0.8, 0.6, 0.4];

                                  // fallback if nothing is available (should be rare)
                                  if (!availableUiVenues || availableUiVenues.length === 0) {
                                    return (
                                      <div className="flex items-center -space-x-2">
                                        <div className="w-8 h-8 rounded-full border-2 border-[#1a1a1a] overflow-hidden bg-white">
                                          <img src="/binance_circle.png" alt="binance" className="w-full h-full object-contain p-0.5" />
                                        </div>
                                      </div>
                                    );
                                  }

                                  if (process.env.NEXT_PUBLIC_UI_DEBUG === 'true') {
                                    // one parity log here is enough to diagnose avatar/series mismatches
                                    // eslint-disable-next-line no-console
                                    console.debug('[AVATAR] availableUiVenues', availableUiVenues);
                                  }

                                  return (
                                    <div className="flex items-center -space-x-2">
                                      {availableUiVenues.map((v, i) => (
                                        <div
                                          key={v}
                                          className="w-8 h-8 rounded-full border-2 border-[#1a1a1a] overflow-hidden bg-white"
                                          style={{ opacity: opacities[i] ?? 0.4 }}
                                          title={v}
                                        >
                                          <img
                                            src={`/${v}_circle.png`}
                                            alt={v}
                                            className="w-full h-full object-contain p-0.5"
                                            loading="eager"
                                          />
                                        </div>
                                      ))}
                                    </div>
                                  );
                                })()}
                        </div>
                      </div>

                            {/* Confidence Display */}
                            {riskSummary && (
                              <div className="mt-3 rounded-lg bg-bg-surface/40 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 relative">
                                {/* top-right time badge — mirror LIVE chip spacing */}
                                <span className="absolute top-3 right-3 inline-flex items-center gap-1.5 bg-bg-tile border border-[#2a2a2a] rounded-full px-2 py-1">
                                  <Clock className="h-3 w-3 text-[#a1a1aa] opacity-70" />
                                  <span className="text-[10px] text-[#a1a1aa] opacity-70">
                                    {riskSummary.source.freshnessSec < 60 
                                      ? `${riskSummary.source.freshnessSec}s ago`
                                      : `${Math.round(riskSummary.source.freshnessSec / 60)}m ago`
                                    }
                                  </span>
                                </span>
                                <div>
                                  <div className="text-sm font-bold text-[#f9fafb]">{riskSummary.confidence}%</div>
                                  <div className="text-xs text-[#a1a1aa]">Statistical Confidence</div>
                                </div>
                              </div>
                            )}
                      </div>

                          <div className="h-80 relative focus:outline-none" style={{ outline: "none" }}>
                            <ResponsiveContainer width="100%" height="100%" style={{ outline: "none" }}>
                          <LineChart data={currentData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                            <XAxis
                              dataKey="date"
                              axisLine={false}
                              tickLine={false}
                              tick={{ fill: "#a1a1aa", fontSize: 10 }}
                              label={{
                                value: "Time",
                                position: "insideBottom",
                                style: { textAnchor: "middle", fill: "#a1a1aa", fontSize: 10 },
                              }}
                            />
                            <YAxis
                              axisLine={false}
                              tickLine={false}
                              tick={{ fill: "#a1a1aa", fontSize: 10 }}
                              label={{
                                    value: exchangeData.length > 0 ? "BTC Price ($)" : "Market Spread %",
                                angle: -90,
                                position: "insideLeft",
                                style: { textAnchor: "middle", fill: "#a1a1aa", fontSize: 10 },
                              }}
                            />
                                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" opacity={0.75} />

                                {/* Option 2: Event Dots - Small colored indicators */}
                                <ReferenceLine
                                  x="Feb '25"
                                  stroke="#ef4444"
                                  strokeOpacity={0}
                                  strokeWidth={0}
                                >
                                  <Label value="●" position="top" />
                                </ReferenceLine>
                                <ReferenceLine
                                  x="Jun '25"
                                  stroke="#f59e0b"
                                  strokeOpacity={0}
                                  strokeWidth={0}
                                >
                                  <Label value="●" position="top" />
                                </ReferenceLine>
                                <ReferenceLine
                                  x="Jul '25"
                                  stroke="#10b981"
                                  strokeOpacity={0}
                                  strokeWidth={0}
                                >
                                  <Label value="●" position="top" />
                                </ReferenceLine>

                                {/* Option 3: Subtle Background Shading - Colored bands for event periods */}
                                <ReferenceLine
                                  x="Feb '25"
                                  stroke="rgba(255, 200, 200, 0.15)"
                                  strokeOpacity={1}
                                  strokeWidth={40}
                                  strokeDasharray="0"
                                />
                                <ReferenceLine
                                  x="Jun '25"
                                  stroke="rgba(255, 220, 180, 0.15)"
                                  strokeOpacity={1}
                                  strokeWidth={40}
                                  strokeDasharray="0"
                                />
                                <ReferenceLine
                                  x="Jul '25"
                                  stroke="rgba(200, 255, 220, 0.15)"
                                  strokeOpacity={1}
                                  strokeWidth={40}
                                  strokeDasharray="0"
                                />

                            <Tooltip
                                  cursor={false}
                              content={({ active, payload, label }: { active?: boolean; payload?: any[]; label?: string }) => {
                                if (active && payload && payload.length) {
                                      // Market share data for each exchange (using live data if available)
                                      const marketShare = exchangeData.length > 0 ? {
                                        Binance: 35,
                                        Coinbase: 25,
                                        Kraken: 20,
                                        Bybit: 20,
                                      } : {
                                        FNB: 21,
                                        ABSA: 21,
                                        "Standard Bank": 26,
                                        Nedbank: 16,
                                      }

                                      // Compute HHI and CR4 from market shares with guardrails
                                      function computeHHIandCR4(sharesPct: (number | null | undefined)[]) {
                                        // Filter out null/undefined/NaN values
                                        const validShares = sharesPct.filter(s => 
                                          s !== null && s !== undefined && !isNaN(s)
                                        );
                                        
                                        // Need at least 2 valid shares to compute meaningful metrics
                                        if (validShares.length < 2) {
                                          return null;
                                        }
                                        
                                        // Round to integers (HHI rule: integer, no commas)
                                        const pctPts = validShares.map(s => Math.round(s as number));
                                        
                                        // HHI: sum of squared percentage points
                                        const hhi = pctPts.reduce((acc, p) => acc + p*p, 0);
                                        
                                        // CR4: sum of top 4 firms, rounded to nearest whole percent
                                        const cr4 = Math.round(
                                          [...pctPts].sort((a,b)=>b-a).slice(0,4).reduce((a,b)=>a+b,0)
                                        );
                                        
                                        return { hhi, cr4 };
                                      }

                                      // Extract shares from marketShare object
                                      const shares = Object.values(marketShare);
                                      const concentrationData = computeHHIandCR4(shares);

                                      // Event data for significant dates
                                      const eventData = {
                                        "Feb '25": {
                                          type: "Fed/Crypto Liquidity Shift",
                                          impact: "Spread/Depth Adaptation",
                                          color: "#ef4444",
                                        },
                                        "Jun '25": {
                                          type: "Market Shock",
                                          impact: "Price Invariance",
                                          color: "#f59e0b",
                                        },
                                        "Jul '25": {
                                          type: "Spread/Depth Adaptation",
                                          impact: "Competitive Response",
                                          color: "#10b981",
                                        },
                                      }

                                      const currentEvent = eventData[label as keyof typeof eventData]

                                  return (
                                        <div className="bg-black border border-[#1a1a1a] rounded-lg p-3 shadow-2xl shadow-black/50">
                                          <p className="text-[#a1a1aa] text-[10px] mb-1.5">{label}</p>
                                          
                                          {/* Concentration Information - only show if valid data */}
                                          {/* Date → Concentration (HHI | CR4) → Optional Event → Bank rows */}
                                          {concentrationData && (
                                            <p className="text-gray-300 text-[10px] font-medium mb-1.5">
                                              Concentration  HHI {concentrationData.hhi} | {concentrationData.cr4}%
                                            </p>
                                          )}

                                          {/* Event Information */}
                                          {currentEvent && (
                                            <div
                                              className="mb-2 p-2 bg-bg-tile rounded border-l-2"
                                              style={{ borderLeftColor: currentEvent.color }}
                                            >
                                              <div className="flex items-center gap-2 mb-1">
                                                <div
                                                  className="w-2 h-2 rounded-full"
                                                  style={{ backgroundColor: currentEvent.color }}
                                                ></div>
                                                <span className="text-[#f9fafb] font-semibold text-[10px]">
                                                  {currentEvent.type}
                                                </span>
                                              </div>
                                              <p className="text-[#a1a1aa] text-[9px]">{currentEvent.impact}</p>
                                            </div>
                                          )}

                                          {/* Exchange/Bank Data - show only plotted series */}
                                      {(() => {
                                        // Map UI venues to their data and values
                                        const rows = availableUiVenues.map(v => {
                                          const k = uiKeyToDataKey[v];
                                          const val = payload?.[0]?.payload?.[k];
                                          return { ui: v, k, val };
                                        }).filter(row => row.val !== undefined);
                                        
                                        return rows.map((row, index) => (
                                          <div key={index} className="flex items-center gap-2 text-[9px]">
                                            <div 
                                              className="w-2 h-2 rounded-full" 
                                              style={{ 
                                                backgroundColor: row.ui === 'binance' ? '#60a5fa' :
                                                               row.ui === 'coinbase' ? '#a1a1aa' :
                                                               row.ui === 'kraken' ? '#71717a' : '#52525b'
                                              }}
                                            />
                                            <span className="text-[#f9fafb] font-semibold">
                                              {row.ui === 'coinbase' ? 'Coinbase' : row.ui.charAt(0).toUpperCase() + row.ui.slice(1)}: <span className="font-bold">${row.val.toFixed(2)}</span> |{" "}
                                              <span className="text-[#a1a1aa]">
                                                {marketShare[row.ui === 'coinbase' ? 'Coinbase' : row.ui.charAt(0).toUpperCase() + row.ui.slice(1) as keyof typeof marketShare]}% share
                                              </span>
                                            </span>
                                          </div>
                                        ));
                                      })()}
                                    </div>
                                      )
                                }
                                    return null
                              }}
                            />
                            {/* Conditional Line components - only mount when data exists */}
                            {(() => {
                              const hasKey = (k: string) => exchangeData.some(p => p[k] !== undefined);
                              return (
                                <>
                                  {hasKey('fnb') && (
                                    <Line
                                      type="monotone"
                                      dataKey="fnb"
                                      stroke="#60a5fa"
                                      strokeWidth={2}
                                      dot={{ fill: "#60a5fa", strokeWidth: 2, r: 3 }}
                                      activeDot={{ r: 4, fill: "#60a5fa" }}
                                      name="Binance"
                                    />
                                  )}
                                  {hasKey('absa') && (
                                    <Line
                                      type="monotone"
                                      dataKey="absa"
                                      stroke="#a1a1aa"
                                      strokeWidth={1.5}
                                      dot={{ fill: "#a1a1aa", strokeWidth: 1.5, r: 2 }}
                                      activeDot={{ r: 3, fill: "#a1a1aa" }}
                                      name="Coinbase"
                                    />
                                  )}
                                  {hasKey('standard') && (
                                    <Line
                                      type="monotone"
                                      dataKey="standard"
                                      stroke="#71717a"
                                      strokeWidth={1.5}
                                      dot={{ fill: "#71717a", strokeWidth: 1.5, r: 2 }}
                                      activeDot={{ r: 3, fill: "#71717a" }}
                                      name="Kraken"
                                    />
                                  )}
                                  {hasKey('nedbank') && (
                                    <Line
                                      type="monotone"
                                      dataKey="nedbank"
                                      stroke="#52525b"
                                      strokeWidth={1.5}
                                      dot={{ fill: "#52525b", strokeWidth: 1.5, r: 2 }}
                                      activeDot={{ r: 3, fill: "#52525b" }}
                                      name="Bybit"
                                    />
                                  )}
                                </>
                              );
                            })()}
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                          {/* Data source indicator */}
                          <div className="text-[9px] text-[#71717a] mt-2 text-center">
                            {exchangeData.length > 0 ? (
                              `Data source: Live Exchange Data • ${exchangeData.length} points • Quality 98%`
                            ) : process.env.NEXT_PUBLIC_PREVIEW_BINANCE === 'true' ? (
                              'Data source: Binance • 15s • Quality 98%'
                            ) : dataSourcesLoading ? (
                              <div className="animate-pulse">
                                <div className="h-3 bg-[#2a2a2a] rounded w-32 mx-auto"></div>
                              </div>
                            ) : dataSourcesError ? (
                              <div className="text-[#fca5a5]">Data source: Error</div>
                            ) : dataSources ? (
                              <>
                                Data source: {dataSources.items[0]?.name || 'Exchange feeds'} • 
                                {dataSources.items[0]?.freshnessSec < 60 
                                  ? `${dataSources.items[0]?.freshnessSec}s` 
                                  : `${Math.round((dataSources.items[0]?.freshnessSec || 0) / 60)}m`
                                } • 
                                Quality {Math.round((dataSources.items[0]?.quality || 0.96) * 100)}%
                              </>
                            ) : (
                              'Data source: Exchange feeds'
                            )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
                {/* Metrics tile: Price Stability, Price Synchronization, Environmental Sensitivity */}
                <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-0">
                    {/* Price Stability */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <TrendingUp className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Price Stability</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  How steady your prices are vs competitors
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">2m ago • 45s</div>
                          </div>
                        </div>
                        <div className="text-right">
                              {metricsLoading ? (
                                <div className="animate-pulse">
                                  <div className="h-4 bg-[#2a2a2a] rounded w-8 mb-1"></div>
                                  <div className="h-3 bg-[#2a2a2a] rounded w-12"></div>
                                </div>
                              ) : metricsError ? (
                                <div className="text-center">
                                  <div className="text-xs text-[#fca5a5] mb-1">Error</div>
                                  <div className="text-[10px] text-[#a1a1aa]">Retry</div>
                                </div>
                              ) : metricsOverview ? (
                                <>
                                  <div className="flex items-center gap-1.5">
                                    <div className="text-[#f9fafb] font-bold text-sm">
                                      {metricsOverview.items.find(m => m.key === 'stability')?.score || 65}
                                    </div>
                                    <div className={`text-xs ${
                                      metricsOverview.items.find(m => m.key === 'stability')?.direction === 'UP' ? 'text-[#fca5a5]' :
                                      metricsOverview.items.find(m => m.key === 'stability')?.direction === 'DOWN' ? 'text-[#a7f3d0]' :
                                      'text-[#a1a1aa]'
                                    }`}>
                                      {metricsOverview.items.find(m => m.key === 'stability')?.direction === 'UP' ? '↑' :
                                       metricsOverview.items.find(m => m.key === 'stability')?.direction === 'DOWN' ? '↓' : '→'}
                                    </div>
                                  </div>
                          <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                                </>
                              ) : (
                                <>
                              <div className="flex items-center gap-1.5">
                                <div className="text-[#f9fafb] font-bold text-sm">65</div>
                                <div className="text-[#fca5a5] text-xs">✗</div>
                              </div>
                          <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                                </>
                              )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Separator line */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>
                    
                    {/* Price Synchronization */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <GitBranch className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Price Sync</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  How closely prices move with others
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">1m ago • 32s</div>
                          </div>
                        </div>
                        <div className="text-right">
                              {metricsLoading ? (
                                <div className="animate-pulse">
                                  <div className="h-4 bg-[#2a2a2a] rounded w-8 mb-1"></div>
                                  <div className="h-3 bg-[#2a2a2a] rounded w-12"></div>
                                </div>
                              ) : metricsError ? (
                                <div className="text-center">
                                  <div className="text-xs text-[#fca5a5] mb-1">Error</div>
                                  <div className="text-[10px] text-[#a1a1aa]">Retry</div>
                                </div>
                              ) : metricsOverview ? (
                                <>
                                  <div className="flex items-center gap-1.5">
                                    <div className="text-[#f9fafb] font-bold text-sm">
                                      {metricsOverview.items.find(m => m.key === 'synchronization')?.score || 18}
                                    </div>
                                    <div className={`text-xs ${
                                      metricsOverview.items.find(m => m.key === 'synchronization')?.direction === 'UP' ? 'text-[#fca5a5]' :
                                      metricsOverview.items.find(m => m.key === 'synchronization')?.direction === 'DOWN' ? 'text-[#a7f3d0]' :
                                      'text-[#a1a1aa]'
                                    }`}>
                                      {metricsOverview.items.find(m => m.key === 'synchronization')?.direction === 'UP' ? '↑' :
                                       metricsOverview.items.find(m => m.key === 'synchronization')?.direction === 'DOWN' ? '↓' : '→'}
                                    </div>
                                  </div>
                                  <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                                </>
                              ) : (
                                <>
                              <div className="flex items-center gap-1.5">
                          <div className="text-[#f9fafb] font-bold text-sm">18</div>
                                <div className="text-[#a7f3d0] text-xs">✓</div>
                              </div>
                          <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                                </>
                              )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Separator line */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>
                    
                    {/* Environmental Sensitivity */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <Activity className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Environmental Sensitivity</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  How well you react to shifts
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">30s ago • 18s</div>
                          </div>
                        </div>
                        <div className="text-right">
                              {metricsLoading ? (
                                <div className="animate-pulse">
                                  <div className="h-4 bg-[#2a2a2a] rounded w-8 mb-1"></div>
                                  <div className="h-3 bg-[#2a2a2a] rounded w-12"></div>
                                </div>
                              ) : metricsError ? (
                                <div className="text-center">
                                  <div className="text-xs text-[#fca5a5] mb-1">Error</div>
                                  <div className="text-[10px] text-[#a1a1aa]">Retry</div>
                                </div>
                              ) : metricsOverview ? (
                                <>
                                  <div className="flex items-center gap-1.5">
                                    <div className="text-[#f9fafb] font-bold text-sm">
                                      {metricsOverview.items.find(m => m.key === 'environmentalSensitivity')?.score || 82}
                                    </div>
                                    <div className={`text-xs ${
                                      metricsOverview.items.find(m => m.key === 'environmentalSensitivity')?.direction === 'UP' ? 'text-[#fca5a5]' :
                                      metricsOverview.items.find(m => m.key === 'environmentalSensitivity')?.direction === 'DOWN' ? 'text-[#a7f3d0]' :
                                      'text-[#a1a1aa]'
                                    }`}>
                                      {metricsOverview.items.find(m => m.key === 'environmentalSensitivity')?.direction === 'UP' ? '↑' :
                                       metricsOverview.items.find(m => m.key === 'environmentalSensitivity')?.direction === 'DOWN' ? '↓' : '→'}
                                    </div>
                                  </div>
                                  <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                                </>
                              ) : (
                                <>
                              <div className="flex items-center gap-1.5">
                          <div className="text-[#f9fafb] font-bold text-sm">82</div>
                                <div className="text-[#a7f3d0] text-xs">✓</div>
                              </div>
                          <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                                </>
                              )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Combined tile: Market Data Feed, Regulatory Notices */}
                <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-0">
                        {/* Bloomberg Data Feed */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                              <Database className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Enable Exchange Data Feed</div>
                                <div className="text-[10px] text-[#a1a1aa]">Real-time trading data and analytics</div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">
                                  Live pricing • Depth • Order flow
                            </div>
                          </div>
                        </div>
                            <div className="ml-4">
                              <button
                                onClick={() => setBloombergDataFeed(!bloombergDataFeed)}
                                className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                  bloombergDataFeed ? "bg-[#86a789]" : "bg-[#374151]"
                                }`}
                              >
                                <div
                                  className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-200 ${
                                    bloombergDataFeed ? "right-0.5" : "left-0.5"
                                  }`}
                                ></div>
                              </button>
                            </div>
                      </div>
                    </div>
                    
                    {/* Separator line */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>
                    
                    {/* Regulatory Notices */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <FileText className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Regulatory Notices</div>
                            <div className="text-[10px] text-[#a1a1aa]">
                              Key compliance updates
                            </div>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          className={dashboardCtaBtnClass}
                        >
                          Connect
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Sixth tile: Assign Reviewers */}
                <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-4 text-center">
                    <h3 className="text-[#f9fafb] font-medium mb-1.5 text-xs">Assign Reviewers</h3>
                    <p className="text-[10px] text-[#a1a1aa] mb-2.5">
                      Invite oversight to review monitoring outputs.
                    </p>
                    <Button
                      className={dashboardCtaBtnClass}
                    >
                      Invite Your Team
                    </Button>
                  </CardContent>
                </Card>
              </div>
            )}
            {/* Configuration Page */}
            {activeSidebarItem === "configuration" && (
              <div className="space-y-6 max-w-2xl">
                {/* Pricing Analysis Settings Section */}
                <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-0">
                    {/* Section Header */}
                    <div className="px-4 py-3 border-b border-[#2a2a2a]">
                          <h2 className="text-sm font-medium text-[#f9fafb]">Coordination Analysis Settings</h2>
                    </div>
                    {/* Configuration Item 1 */}
                    <div className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Activity className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">
                                    Automatically Detect Market Changes
                          </div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Auto-detect significant market shifts
                                  </div>
                                </div>
                              </div>
                        </div>
                        <div className="ml-4">
                          <button 
                            onClick={() => setAutoDetectMarketChanges(!autoDetectMarketChanges)}
                            className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                  autoDetectMarketChanges ? "bg-[#86a789]" : "bg-[#374151]"
                                }`}
                              >
                                <div
                                  className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-200 ${
                                    autoDetectMarketChanges ? "right-0.5" : "left-0.5"
                                  }`}
                                ></div>
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    {/* Horizontal Divider */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>
                    
                    {/* Configuration Item 2 */}
                    <div className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <TrendingUp className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">Price Change Threshold</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Trigger level for analysis
                          </div>
                        </div>
                              </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={changeThreshold}
                            onChange={(e) => setChangeThreshold(e.target.value)}
                                className="bg-bg-tile border border-[#2a2a2a] rounded-md px-3 py-1.5 text-xs text-[#f9fafb] cursor-pointer hover:bg-[#2a2a2a] focus:border-[#60a5fa] focus:outline-none focus:ring-1 focus:ring-[#60a5fa] transition-colors duration-200 appearance-none pr-8"
                              >
                                <option value="5%">5%</option>
                                <option value="10%">10%</option>
                                <option value="15%">15%</option>
                                <option value="20%">20%</option>
                                <option value="25%">25%</option>
                              </select>
                              <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-3 h-3 text-[#71717a] pointer-events-none" />
                        </div>
                      </div>
                    </div>
                    
                    {/* Horizontal Divider */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>
                    
                    {/* Configuration Item 3 */}
                    <div className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <BarChart3 className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                            <div className="text-xs font-medium text-[#f9fafb]">Confidence Level</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Confidence required for alerts
                          </div>
                        </div>
                              </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={confidenceLevel}
                            onChange={(e) => setConfidenceLevel(e.target.value)}
                                className="w-20 h-8 bg-bg-tile border border-[#2a2a2a] rounded text-xs text-[#f9fafb] text-center appearance-none cursor-pointer hover:bg-[#2a2a2a] transition-colors duration-200 pr-6"
                              >
                                <option value="95%">95%</option>
                                <option value="90%">90%</option>
                                <option value="85%">85%</option>
                                <option value="80%">80%</option>
                                <option value="75%">75%</option>
                                <option value="70%">70%</option>
                              </select>
                              <ChevronDown className="absolute right-1 top-1/2 transform -translate-y-1/2 w-3 h-3 text-[#a1a1aa] pointer-events-none" />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Monitoring Engine Settings Section */}
                <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-0">
                    {/* Section Header */}
                    <div className="px-4 py-3 border-b border-[#2a2a2a]">
                      <h2 className="text-sm font-medium text-[#f9fafb]">Monitoring Engine Settings</h2>
                    </div>
                    {/* Configuration Item 1 */}
                    <div className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Zap className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                            <div className="text-xs font-medium text-[#f9fafb]">Enable Live Monitoring</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Real-time risk analysis
                          </div>
                                </div>
                              </div>
                        </div>
                        <div className="ml-4">
                          <button 
                            onClick={() => setEnableLiveMonitoring(!enableLiveMonitoring)}
                            className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                  enableLiveMonitoring ? "bg-[#86a789]" : "bg-[#374151]"
                                }`}
                              >
                                <div
                                  className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-200 ${
                                    enableLiveMonitoring ? "right-0.5" : "left-0.5"
                                  }`}
                                ></div>
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    {/* Horizontal Divider */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>
                    
                    {/* Configuration Item 2 */}
                    <div className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Clock className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                            <div className="text-xs font-medium text-[#f9fafb]">Update Frequency</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">Analysis interval</div>
                          </div>
                        </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={updateFrequency}
                            onChange={(e) => setUpdateFrequency(e.target.value)}
                                className="w-20 h-8 bg-bg-tile border border-[#2a2a2a] rounded text-xs text-[#f9fafb] text-center appearance-none cursor-pointer hover:bg-[#2a2a2a] transition-colors duration-200 pr-6"
                              >
                                <option value="1m">1m</option>
                                <option value="5m">5m</option>
                                <option value="10m">10m</option>
                                <option value="15m">15m</option>
                                <option value="30m">30m</option>
                                <option value="1h">1h</option>
                              </select>
                              <ChevronDown className="absolute right-1 top-1/2 transform -translate-y-1/2 w-3 h-3 text-[#a1a1aa] pointer-events-none" />
                        </div>
                      </div>
                    </div>
                    
                    {/* Horizontal Divider */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>
                    
                    {/* Configuration Item 3 */}
                    <div className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Settings className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                            <div className="text-xs font-medium text-[#f9fafb]">Sensitivity Level</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Detection sensitivity
                          </div>
                        </div>
                              </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={sensitivityLevel}
                            onChange={(e) => setSensitivityLevel(e.target.value)}
                                className="w-20 h-8 bg-bg-tile border border-[#2a2a2a] rounded text-xs text-[#f9fafb] text-center appearance-none cursor-pointer hover:bg-[#2a2a2a] transition-colors duration-200 pr-6"
                              >
                                <option value="Low">Low</option>
                                <option value="Medium">Medium</option>
                                <option value="High">High</option>
                              </select>
                              <ChevronDown className="absolute right-1 top-1/2 transform -translate-y-1/2 w-3 h-3 text-[#a1a1aa] pointer-events-none" />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Data Quality Controls Section */}
                <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-0">
                    {/* Section Header */}
                    <div className="px-4 py-3 border-b border-[#2a2a2a]">
                      <h2 className="text-sm font-medium text-[#f9fafb]">Data Quality Controls</h2>
                    </div>
                    {/* Configuration Item 1 */}
                    <div className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <ShieldCheck className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                            <div className="text-xs font-medium text-[#f9fafb]">Check Data Quality</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Validate accuracy and consistency
                          </div>
                                </div>
                              </div>
                        </div>
                        <div className="ml-4">
                          <button 
                            onClick={() => setCheckDataQuality(!checkDataQuality)}
                            className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                  checkDataQuality ? "bg-[#86a789]" : "bg-[#374151]"
                                }`}
                              >
                                <div
                                  className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-200 ${
                                    checkDataQuality ? "right-0.5" : "left-0.5"
                                  }`}
                                ></div>
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    {/* Horizontal Divider */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>
                    
                    {/* Configuration Item 2 */}
                    <div className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Clock className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                            <div className="text-xs font-medium text-[#f9fafb]">Max Data Age</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Max age before backup
                          </div>
                        </div>
                              </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={maxDataAge}
                            onChange={(e) => setMaxDataAge(e.target.value)}
                                className="w-20 h-8 bg-bg-tile border border-[#2a2a2a] rounded text-xs text-[#f9fafb] text-center appearance-none cursor-pointer hover:bg-[#2a2a2a] transition-colors duration-200 pr-6"
                              >
                                <option value="10m">10m</option>
                                <option value="30m">30m</option>
                                <option value="1h">1h</option>
                                <option value="24h">24h</option>
                              </select>
                              <ChevronDown className="absolute right-1 top-1/2 transform -translate-y-1/2 w-3 h-3 text-[#a1a1aa] pointer-events-none" />
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
                {/* Data Sources Page */}
                {activeSidebarItem === "data-sources" && (
                  <div className="space-y-6">
                    {/* Connect Your Data */}
                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-0">
                        {/* Section Header */}
                        <div className="px-4 py-3 border-b border-[#2a2a2a]">
                          <h2 className="text-sm font-medium text-[#f9fafb]">Connect Your Data</h2>
                        </div>
                        {/* Configuration Items */}
                        <div className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Upload className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">File Upload</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    CSV, JSON, Parquet files • Up to 100MB
                                  </div>
                                </div>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              className={dashboardCtaBtnClass}
                            >
                              Connect
                            </Button>
                          </div>
                        </div>
                        <div
                          className="px-4 py-3 border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Zap className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">API Integration</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Real-time pricing feeds • REST/GraphQL
                                  </div>
                                </div>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              className={dashboardCtaBtnClass}
                            >
                              Connect
                            </Button>
                          </div>
                        </div>
                        <div
                          className="px-4 py-3 border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Database className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">Database Connection</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    PostgreSQL, MongoDB • Direct connection
                                  </div>
                                </div>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              className={dashboardCtaBtnClass}
                            >
                              Connect
                            </Button>
                          </div>
                        </div>
                        <div
                          className="px-4 py-3 border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Cloud className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">Cloud Storage</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    S3, Azure Blob • Automated sync
                                  </div>
                                </div>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              className={dashboardCtaBtnClass}
                            >
                              Connect
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* API Keys */}
                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-4">
                        <h3 className="text-xs font-medium text-[#f9fafb] mb-3">API Keys</h3>
                        <div className="space-y-2">
                          <button className="w-full text-left p-3 bg-bg-surface hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors flex items-center justify-between">
                            <div>
                              <div className="font-medium">Generate new API key</div>
                              <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                Create secure access tokens for data integration
                              </div>
                            </div>
                            <SquarePlus className="w-4 h-4 text-[#a1a1aa] flex-shrink-0" />
                          </button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
                {/* AI Economists Page */}
                {activeSidebarItem === "ai-economists" && (
                  <div className="space-y-6">
                    {/* Quick Analysis */}
                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-4">
                        {/* Updated Quick Analysis header font size from text-xs to text-sm */}
                        <h3 className="text-sm font-medium text-[#f9fafb] mb-3">Quick Analysis</h3>
                        <div className="space-y-2">
                          <button className="w-full text-left p-3 bg-bg-surface hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors flex items-center justify-between">
                            <div>
                              <div className="font-medium">Analyze Pricing</div>
                              <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                Identify trends and anomalies
                              </div>
                            </div>
                            <SquareChevronRight className="w-4 h-4 text-[#a1a1aa] flex-shrink-0" />
                          </button>
                          <button className="w-full text-left p-3 bg-bg-surface hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors flex items-center justify-between">
                            <div>
                              <div className="font-medium">Check Compliance</div>
                              <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                Review regulatory gaps
                              </div>
                            </div>
                            <SquareChevronRight className="w-4 h-4 text-[#a1a1aa] flex-shrink-0" />
                          </button>
                          <button className="w-full text-left p-3 bg-bg-surface hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors flex items-center justify-between">
                            <div>
                              <div className="font-medium">Generate Report</div>
                              <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                Comprehensive analysis doc
                              </div>
                            </div>
                            <SquareChevronRight className="w-4 h-4 text-[#a1a1aa] flex-shrink-0" />
                          </button>
                          <button 
                            onClick={handleEvidenceExport}
                            disabled={evidenceLoading}
                            className="w-full text-left p-3 bg-bg-surface hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors flex items-center justify-between disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <div>
                              <div className="font-medium">
                                {evidenceLoading ? 'Generating...' : 'Evidence Bundle'}
                              </div>
                              <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                Cryptographic timestamps
                              </div>
                            </div>
                            <SquareChevronRight className="w-4 h-4 text-[#a1a1aa] flex-shrink-0" />
                          </button>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Available Agents */}
                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-0">
                        {/* Section Header */}
                        <div className="px-4 py-3 border-b border-[#2a2a2a]">
                          <h2 className="text-sm font-medium text-[#f9fafb]">Agent Type</h2>
                        </div>
                        {/* Configuration Items */}
                        <div className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <Brain className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">General Analyst</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Accuracy: 94.2% • Response time: 1.2s
                                  </div>
                                </div>
                              </div>
                            </div>
                            <button 
                              onClick={() => setActiveAgent(activeAgent === "general" ? null : "general")}
                              className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                activeAgent === "general" ? "bg-[#86a789]" : "bg-[#374151]"
                              }`}
                              aria-pressed={activeAgent === "general"}
                            >
                              <div
                                className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-200 ${
                                  activeAgent === "general" ? "right-0.5" : "left-0.5"
                                }`}
                              ></div>
                            </button>
                          </div>
                        </div>
                        <div
                          className="px-4 py-3 border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <ScaleIcon className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">Competition Lawyer</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Accuracy: 97.8% • Response time: 2.1s
                                  </div>
                                </div>
                              </div>
                            </div>
                            <button 
                              onClick={() => setActiveAgent(activeAgent === "compliance" ? null : "compliance")}
                              className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                activeAgent === "compliance" ? "bg-[#86a789]" : "bg-[#374151]"
                              }`}
                              aria-pressed={activeAgent === "compliance"}
                            >
                              <div
                                className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-200 ${
                                  activeAgent === "compliance" ? "right-0.5" : "left-0.5"
                                }`}
                              ></div>
                            </button>
                          </div>
                        </div>
                        <div
                          className="px-4 py-3 border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <TrendingUp className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">Pricing Economist</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Accuracy: 96.1% • Response time: 1.8s
                                  </div>
                                </div>
                              </div>
                            </div>
                            <button 
                              onClick={() => setActiveAgent(activeAgent === "pricing" ? null : "pricing")}
                              className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                activeAgent === "pricing" ? "bg-[#86a789]" : "bg-[#374151]"
                              }`}
                              aria-pressed={activeAgent === "pricing"}
                            >
                              <div
                                className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-200 ${
                                  activeAgent === "pricing" ? "right-0.5" : "left-0.5"
                                }`}
                              ></div>
                            </button>
                          </div>
                        </div>
                        <div
                          className="px-4 py-3 border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-start gap-2">
                                <BarChart3 className="w-4 h-4 text-[#a1a1aa] self-center" />
                                <div>
                                  <div className="text-xs font-medium text-[#f9fafb]">Data Scientist</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Accuracy: 95.7% • Response time: 1.5s
                                  </div>
                                </div>
                              </div>
                            </div>
                            <button 
                              onClick={() => setActiveAgent(activeAgent === "data" ? null : "data")}
                              className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                activeAgent === "data" ? "bg-[#86a789]" : "bg-[#374151]"
                              }`}
                              aria-pressed={activeAgent === "data"}
                            >
                              <div
                                className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-200 ${
                                  activeAgent === "data" ? "right-0.5" : "left-0.5"
                                }`}
                              ></div>
                            </button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
                {/* Health Checks Page */}
                {activeSidebarItem === "health-checks" && (
                  <div className="space-y-3 max-w-2xl">
                    {/* Top tile - Copy of 2nd tile from Overview (with graph) */}
                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-xs font-medium text-[#f9fafb]">Your System Integrity</h3>
                          <div className="flex gap-2">
                            <button
                              onClick={() => setSelectedTimeframe("30d")}
                              className={`text-xs px-2 py-1 ${selectedTimeframe === "30d" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                            >
                              30d
                            </button>
                            <button
                              onClick={() => setSelectedTimeframe("6m")}
                              className={`text-xs px-2 py-1 ${selectedTimeframe === "6m" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                            >
                              6m
                            </button>
                            <button
                              onClick={() => setSelectedTimeframe("1y")}
                              className={`text-xs px-2 py-1 ${selectedTimeframe === "1y" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                            >
                              1y
                            </button>
                            <button
                              onClick={() => setSelectedTimeframe("ytd")}
                              className={`text-xs px-2 py-1 ${selectedTimeframe === "ytd" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                            >
                              YTD
                            </button>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 mb-10">
                          <div className="rounded-lg bg-bg-surface shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                            <div className="text-xl font-bold text-[#f9fafb]">84 out of 100</div>
                            <div className="text-xs text-[#a7f3d0]">Pass</div>
                          </div>
                          <div className="rounded-lg bg-bg-surface/40 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                            <div className="text-xl font-bold text-[#f9fafb]">67%</div>
                            <div className="text-xs text-[#a1a1aa]">Compliance Readiness</div>
                          </div>
                        </div>

                        <div className="h-80">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                              data={[
                                {
                                  date: "Jan 25",
                                  "Convergence Rate": 25,
                                  "Data Integrity": 18,
                                  "Evidence Chain": 82,
                                  "Runtime Stability": 81,
                                },
                                {
                                  date: "Feb 25",
                                  "Convergence Rate": 28,
                                  "Data Integrity": 22,
                                  "Evidence Chain": 85,
                                  "Runtime Stability": 79,
                                },
                                {
                                  date: "Mar 25",
                                  "Convergence Rate": 32,
                                  "Data Integrity": 25,
                                  "Evidence Chain": 88,
                                  "Runtime Stability": 83,
                                },
                                {
                                  date: "Apr 25",
                                  "Convergence Rate": 29,
                                  "Data Integrity": 19,
                                  "Evidence Chain": 84,
                                  "Runtime Stability": 77,
                                },
                                {
                                  date: "May 25",
                                  "Convergence Rate": 35,
                                  "Data Integrity": 28,
                                  "Evidence Chain": 90,
                                  "Runtime Stability": 85,
                                },
                                {
                                  date: "Jun 25",
                                  "Convergence Rate": 31,
                                  "Data Integrity": 24,
                                  "Evidence Chain": 87,
                                  "Runtime Stability": 82,
                                },
                                {
                                  date: "Jul 25",
                                  "Convergence Rate": 38,
                                  "Data Integrity": 31,
                                  "Evidence Chain": 92,
                                  "Runtime Stability": 88,
                                },
                                {
                                  date: "Aug 25",
                                  "Convergence Rate": 42,
                                  "Data Integrity": 35,
                                  "Evidence Chain": 94,
                                  "Runtime Stability": 91,
                                },
                              ]}
                              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                            >
                              <XAxis
                                dataKey="date"
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: "#a1a1aa", fontSize: 10 }}
                              />
                              <YAxis
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: "#a1a1aa", fontSize: 10 }}
                                label={{
                                  value: "System Health Score",
                                  angle: -90,
                                  position: "insideLeft",
                                  style: { textAnchor: "middle", fill: "#a1a1aa", fontSize: 10 },
                                }}
                              />
                              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" opacity={0.75} />

                              <Tooltip
                                cursor={false}
                                content={({ active, payload, label }: { active?: boolean; payload?: any[]; label?: string }) => {
                                  if (active && payload && payload.length) {
                                    return (
                                      <div className="bg-black border border-[#1a1a1a] rounded-lg p-3 shadow-2xl shadow-black/50">
                                        <p className="text-[#a1a1aa] text-[10px] mb-1.5">{label}</p>
                                        {payload.map((entry: any, index: number) => (
                                          <div key={index} className="flex items-center gap-2 text-[9px]">
                                            <div
                                              className="w-2 h-2 rounded-full"
                                              style={{ backgroundColor: entry.color }}
                                            />
                                            <span className="text-[#f9fafb] font-semibold">
                                              {entry.name}: <span className="font-bold">{entry.value}/100</span>
                                            </span>
                        </div>
                                        ))}
                      </div>
                                    )
                                  }
                                  return null
                                }}
                              />
                              <Line
                                type="monotone"
                                dataKey="Convergence Rate"
                                stroke="#a8b2d1"
                                strokeWidth={2}
                                dot={{ fill: "#a8b2d1", strokeWidth: 0, r: 3 }}
                                activeDot={{ r: 4, stroke: "#a8b2d1", strokeWidth: 2, fill: "#0f0f10" }}
                              />
                              <Line
                                type="monotone"
                                dataKey="Data Integrity"
                                stroke="#b5c4a8"
                                strokeWidth={2}
                                dot={{ fill: "#b5c4a8", strokeWidth: 0, r: 3 }}
                                activeDot={{ r: 4, stroke: "#b5c4a8", strokeWidth: 2, fill: "#0f0f10" }}
                              />
                              <Line
                                type="monotone"
                                dataKey="Evidence Chain"
                                stroke="#d4a5a5"
                                strokeWidth={2}
                                dot={{ fill: "#d4a5a5", strokeWidth: 0, r: 3 }}
                                activeDot={{ r: 4, stroke: "#d4a5a5", strokeWidth: 2, fill: "#0f0f10" }}
                              />
                              <Line
                                type="monotone"
                                dataKey="Runtime Stability"
                                stroke="#a8a8b5"
                                strokeWidth={2}
                                dot={{ fill: "#a8a8b5", strokeWidth: 0, r: 3 }}
                                activeDot={{ r: 4, stroke: "#a8a8b5", strokeWidth: 2, fill: "#0f0f10" }}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                        {/* Data source indicator */}
                        <div className="text-[9px] text-[#71717a] mt-2 text-center">
                          Data source: Internal Monitoring
                        </div>
                      </CardContent>
                    </Card>

                    {/* Bottom tile - Copy of 3rd tile from Overview (with 4 rows of content) */}
                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-0">
                        {/* Convergence Rate */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Target className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Convergence Rate</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  How often the model runs without errors
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">2m ago • 45s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1.5">
                                <div className="text-[#f9fafb] font-bold text-sm">25</div>
                                <div className="text-[#fca5a5] text-xs">✗</div>
                              </div>
                              <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                            </div>
                          </div>
                        </div>

                        {/* Separator line */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* Data Integrity */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Shield className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Data Integrity</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Checks if market data is valid and clean
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">5m ago • 1m 12s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1.5">
                                <div className="text-[#f9fafb] font-bold text-sm">18</div>
                                <div className="text-[#a7f3d0] text-xs">✓</div>
                              </div>
                              <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                            </div>
                          </div>
                        </div>

                        {/* Separator line */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* Evidence Chain */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Link className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Evidence Chain</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Ensures results are timestamped for audit
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">30s ago • 18s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1.5">
                                <div className="text-[#f9fafb] font-bold text-sm">82</div>
                                <div className="text-[#a7f3d0] text-xs">✓</div>
                              </div>
                              <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                            </div>
                          </div>
                        </div>

                        {/* Separator line */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* Runtime Stability */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Gauge className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Runtime Stability</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Tracks run speed vs targets
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">Updated just now</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1.5">
                                <div className="text-[#f9fafb] font-bold text-sm">81</div>
                                <div className="text-[#a7f3d0] text-xs">✓</div>
                              </div>
                              <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                            </div>
                          </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
                )}
                {/* Events Log Page */}
                {activeSidebarItem === "events-log" && (
                  <div className="space-y-3 max-w-2xl">
                    {/* Simplified header with responsive layout */}
                    <div className="bg-transparent overflow-x-hidden px-4">
                      <div className="flex flex-wrap items-center gap-2 justify-between mb-4">
                        {/* Right Container - Log Event Button */}
                        <div className="flex justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs bg-transparent border-[#2a2a2a] text-[#f9fafb] hover:bg-bg-tile"
                            onClick={() => {
                              setActiveTab("agents")
                              setInitialAgentMessage("")
                              // Trigger the event logging flow
                              setTimeout(() => {
                                handleSendMessage("Help me log a market event")
                              }, 100)
                            }}
                          >
                            <SquarePen className="w-3 h-3 mr-1" />
                            Log event
                          </Button>
                        </div>
                      </div>
                    </div>

                    <EventsTable 
                      timeframe={selectedTimeframe}
                      region="US"
                      industry="CRYPTO"
                      onLogEvent={() => {
                        setActiveTab("agents")
                        setInitialAgentMessage("")
                        // Trigger the event logging flow
                        setTimeout(() => {
                          handleSendMessage("Help me log a market event")
                        }, 100)
                      }}
                    />
                  </div>
                )}

                {/* Billing Page */}
                {activeSidebarItem === "billing" && (
                  <div className="space-y-6 max-w-4xl">
                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-6">
                        {/* Title Section */}
                        <div className="mb-4">
                          <h3 className="text-xs font-medium text-[#f9fafb]">Your Invoice</h3>
                        </div>

                        {/* Left and Right Containers */}
                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 mb-10">
                          {/* Left Container - Pricing Info */}
                          <div className="rounded-lg bg-bg-surface shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                            <div className="text-xl font-bold text-[#f9fafb]">US$ 0.00</div>
                            <div className="text-xs text-[#a1a1aa]">September 2025</div>
                          </div>
                          {/* Right Container - Empty and Transparent */}
                          <div className="rounded-lg bg-transparent p-3"></div>
                        </div>

                        {/* General Content Area - Table Content */}
                        <div className="overflow-hidden">
                          <table className="w-full">
                            <thead>
                              <tr className="border-b border-[#2a2a2a]/70">
                                <th className="text-left text-xs text-[#a1a1aa] font-medium pb-3">Type</th>
                                <th className="text-right text-xs text-[#a1a1aa] font-medium pb-3">Cost</th>
                                <th className="text-right text-xs text-[#a1a1aa] font-medium pb-3">Qty</th>
                                <th className="text-right text-xs text-[#a1a1aa] font-medium pb-3">Total</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr className="border-b border-[#2a2a2a]/70">
                                <td className="py-3 text-xs text-[#f9fafb]">Subtotal:</td>
                                <td className="text-right text-xs text-[#f9fafb] py-3"></td>
                                <td className="text-right text-xs text-[#f9fafb] py-3"></td>
                                <td className="text-right text-xs text-[#f9fafb] py-3">US$0.00</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>

                        <div className="mt-6 text-center text-[10px] text-[#a1a1aa]">
                          No invoices found for September 2025
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* Compliance Reports Page */}
                {activeSidebarItem === "compliance" && (
                  <div className="space-y-3 max-w-2xl">
                    {/* Simplified header with mobile-responsive layout */}
                    <div className="bg-transparent">
                      <div className="flex items-center justify-between mb-4">
                        {/* Date Range and Time Tabs - Hidden on mobile */}
                        <div className="hidden md:flex items-center gap-4 report-filters">
                          {/* Date Range Button */}
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs bg-transparent border-[#2a2a2a] text-[#f9fafb] hover:bg-bg-tile"
                          >
                            Jan 01 - Sep 05
                            <ChevronDown className="w-3 h-3 ml-1" />
                          </Button>

                          {/* Time Tabs */}
                          <div className="flex gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-bg-tile hover:text-[#f9fafb]"
                            >
                              30d
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-bg-tile hover:text-[#f9fafb]"
                            >
                              6m
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-bg-tile hover:text-[#f9fafb]"
                            >
                              1y
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-bg-tile border-[#2a2a2a] text-[#f9fafb]"
                            >
                              YTD
                            </Button>
                          </div>
                        </div>

                        {/* Export ZIP Button - Always visible, right-aligned */}
                        <div className="flex justify-end ml-auto min-w-max">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs bg-transparent border-[#2a2a2a] text-[#f9fafb] hover:bg-bg-tile"
                            onClick={handleEvidenceExport}
                            disabled={evidenceLoading}
                          >
                            <Download className="w-3 h-3 mr-1" />
                            {evidenceLoading ? 'Generating...' : 'Export ZIP'}
                          </Button>
                        </div>
                      </div>
                    </div>

                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-0">
                        {/* Title Section */}
                        <div className="px-4 py-3 border-b border-[#2a2a2a]">
                          <h2 className="text-sm font-medium text-[#f9fafb]">All Reports</h2>
                        </div>

                        {/* Event Status 1 */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <ShieldCheck className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Monthly Compliance Report</div>
                                <div 
                                  className="text-[10px] text-[#a1a1aa]"
                                  title="Healthy: 3 instances of competitive adaptation to regime breaks"
                                  aria-label="Healthy: 3 instances of competitive adaptation to regime breaks"
                                >
                                  {truncateText("Healthy: 3 instances of competitive adaptation to regime breaks")}
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">2m ago • 45s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                className={dashboardCtaBtnClass}
                              >
                                Download
                              </Button>
                            </div>
                          </div>
                        </div>

                        {/* Separator line */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* Event Status 2 */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Moon className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Nightly Competitive Assessment</div>
                                <div 
                                  className="text-[10px] text-[#a1a1aa]"
                                  title="Spread Dispersion of 17 bps, ↑ +15% in 24 hrs"
                                  aria-label="Spread Dispersion of 17 bps, ↑ +15% in 24 hrs"
                                >
                                  {truncateText("Spread Dispersion of 17 bps, ↑ +15% in 24 hrs")}
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">1m ago • 32s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                className={dashboardCtaBtnClass}
                              >
                                Download
                              </Button>
                            </div>
                          </div>
                        </div>

                        {/* Separator line */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* Event Status 3 */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Scale className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Quarterly Evidence Bundle</div>
                                <div 
                                  className="text-[10px] text-[#a1a1aa]"
                                  title="96.8% statistical confidence over 18-month view"
                                  aria-label="96.8% statistical confidence over 18-month view"
                                >
                                  {truncateText("96.8% statistical confidence over 18-month view")}
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">30s ago • 18s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                className={dashboardCtaBtnClass}
                              >
                                Download
                              </Button>
                            </div>
                          </div>
                        </div>

                        {/* Pagination Info */}
                        <div className="px-4 py-3 border-t border-[#2a2a2a]">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4 text-[10px] text-[#a1a1aa]">
                              <span>Showing 1 – 3 of 3 reports</span>
                              <div className="flex items-center gap-2">
                                <span>Rows per page:</span>
                                <select 
                                  className="bg-transparent border border-[#2a2a2a] rounded px-2 py-1 text-[#f9fafb] text-[10px]"
                                  aria-label="Rows per page"
                                >
                                  <option value="50">50</option>
                                  <option value="100">100</option>
                                </select>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* Contact Us Page */}
                {activeSidebarItem === "contact" && (
                  <div className="space-y-3 max-w-2xl">
                    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-4">
                        <h2 className="text-sm font-medium text-[#f9fafb] mb-2">Contact Us</h2>
                        <p className="text-xs text-[#a1a1aa] leading-relaxed">
                          For all support inquiries, including billing issues, receipts, and general assistance, please
                          email{" "}
                          <a href="mailto:hello@RBB.ai" className="text-[#60a5fa] hover:text-[#93c5fd] underline">
                            hello@RBB.ai
                          </a>
                          .
                        </p>
                      </CardContent>
                    </Card>
                  </div>
                )}
              </>
            )}
          </main>
        </div>
      </div>

      {/* GitHub Modal */}
      {isGitHubModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-96 max-w-[90vw] shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <Github className="h-6 w-6 text-[#f9fafb]" />
              <h3 className="text-lg font-medium text-[#f9fafb]">Link GitHub Repository</h3>
            </div>
            <p className="text-sm text-zinc-300 mb-4">
              Enter the URL of the GitHub repository you want to connect:
            </p>
            <input
              type="url"
              value={gitHubRepoUrl}
              onChange={(e) => setGitHubRepoUrl(e.target.value)}
              placeholder="https://github.com/username/repository"
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-[#f9fafb] placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#86a789] focus:border-transparent"
              autoFocus
            />
            <div className="flex gap-3 mt-6 justify-end">
              <button
                onClick={() => {
                  setGitHubRepoUrl("")
                  setIsGitHubModalOpen(false)
                }}
                className="px-4 py-2 text-sm text-zinc-300 hover:text-[#f9fafb] border border-zinc-700 rounded-md hover:bg-zinc-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleGitHubConnect}
                disabled={!gitHubRepoUrl.trim()}
                className="px-4 py-2 text-sm bg-[#86a789] text-white rounded-md hover:bg-[#7a9a7a] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Connect
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}

