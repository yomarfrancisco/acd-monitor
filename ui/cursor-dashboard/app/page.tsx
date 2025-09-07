"use client"

import { Separator } from "@/components/ui/separator"

import { useState, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Bot,
  FileText,
  Zap,
  Send,
  ChevronDown,
  User,
  Settings,
  Database,
  Activity,
  Scale,
  TrendingUp,
  Clock,
  Download,
  Upload,
  Server,
  Cloud,
  SquareChevronRight,
} from "lucide-react"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts"
import { CalendarIcon } from "lucide-react"
import {
  MessageSquare,
  BarChart3,
  GitBranch,
  ClipboardList,
  CreditCardIcon,
  CloudUpload,
  ChevronRight,
  CalendarCheck2,
  ShieldCheck,
  Moon,
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

export default function CursorDashboard() {
  const [activeTab, setActiveTab] = useState<"agents" | "dashboard">("agents")
  const [selectedTimeframe, setSelectedTimeframe] = useState<"30d" | "6m" | "1y" | "YTD">("YTD")
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)
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
  const [selectedAgent, setSelectedAgent] = useState("General Analysis")
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([])

  // Configuration input field states
  const [changeThreshold, setChangeThreshold] = useState("5%")
  const [confidenceLevel, setConfidenceLevel] = useState("95%")
  const [updateFrequency, setUpdateFrequency] = useState("5m")
  const [sensitivityLevel, setSensitivityLevel] = useState("Medium")
  const [maxDataAge, setMaxDataAge] = useState("10m")
  const [autoDetectMarketChanges, setAutoDetectMarketChanges] = useState(true)
  const [enableLiveMonitoring, setEnableLiveMonitoring] = useState(true)
  const [checkDataQuality, setCheckDataQuality] = useState(true)

  useEffect(() => {
    setIsClient(true)
  }, [])

  // Close calendar when switching to agents tab
  const handleTabChange = (tab: "agents" | "dashboard") => {
    setActiveTab(tab)
    if (tab === "agents") setIsCalendarOpen(false)
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
      case "YTD":
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
        <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-6">
              <div className="rounded-lg bg-[#1a1a1a] shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                <div>
                  <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Left Container</h2>
                  <p className="text-xs text-[#a1a1aa] mb-3 leading-relaxed">
                    Shell content for {pageTitle} - Left side
                  </p>
                </div>
                <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-[#1a1a1a] text-[#a1a1aa] hover:text-[#f9fafb] self-start">
                  Action Button
                </button>
              </div>
              <div className="rounded-lg bg-[#1e1e1e] shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                <div>
                  <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Right Container</h2>
                  <p className="text-xs text-[#a1a1aa] mb-3 leading-relaxed">
                    Shell content for {pageTitle} - Right side
                  </p>
                </div>
                <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-[#1a1a1a] text-[#a1a1aa] hover:text-[#f9fafb] self-start">
                  Action Button
                </button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Second shell tile */}
        <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
          <CardContent className="p-4 text-center">
            <h3 className="text-[#f9fafb] font-medium mb-1.5 text-xs">Second Shell Tile</h3>
            <p className="text-[10px] text-[#a1a1aa] mb-2.5">Additional shell content for {pageTitle} page.</p>
            <Button
              variant="outline"
              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
            >
              Shell Action
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const currentData = getAnalyticsData()

  return (
    <div className="min-h-screen bg-[#0f0f10] text-[#f9fafb] font-sans p-4">
      {/* Header */}
      <header className="border-b border-[#1a1a1a] px-5 py-1.5 relative">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img 
              src="/rbb-economics-logo.png" 
              alt="RBB Economics" 
              className="h-28 w-auto opacity-90 hover:opacity-100 transition-opacity"
            />
          </div>

          <nav className="flex gap-5 absolute left-1/2 transform -translate-x-1/2">
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
              Dashboard
            </button>
          </nav>

          <div className="text-xs font-medium text-[#f9fafb] bg-[#1a1a1a] rounded-full w-7 h-7 flex items-center justify-center">
            YF
          </div>
        </div>
      </header>

      {/* Extra spacing below header */}
      <div className="h-6"></div>

      <div className="flex justify-center">
        <div className="flex max-w-5xl w-full">
          {/* Sidebar - Only show on dashboard */}
          {activeTab === "dashboard" && (
            <aside className="w-64 bg-[#0f0f10] p-3 flex-shrink-0">
              <div className="space-y-3">
                {/* User Info */}
                <div>
                  <h3 className="text-xs font-semibold text-[#f9fafb] mb-1">Ygor Francisco</h3>
                  <p className="text-[10px] text-[#a1a1aa] mb-2.5">Ent Plan · ygor.francisco@gmail.com</p>

                  <div
                    className={`rounded-md p-1.5 mb-2.5 cursor-pointer ${activeSidebarItem === "overview" ? "bg-[#1a1a1a]" : "hover:bg-[#1a1a1a]"}`}
                    onClick={() => setActiveSidebarItem("overview")}
                  >
                    <div className="flex items-center gap-2 text-xs font-medium text-[#f9fafb]">
                      <User className="w-3.5 h-3.5" />
                      Overview
                    </div>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div
                      className={`flex items-center gap-2 px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "configuration" ? "bg-[#1a1a1a] text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-[#1a1a1a]"}`}
                      onClick={() => setActiveSidebarItem("configuration")}
                    >
                      <Settings className="w-3.5 h-3.5" />
                      Configuration
                    </div>
                  </div>
                </div>

                <Separator className="bg-[#1a1a1a]" />

                {/* Navigation */}
                <nav className="space-y-0.5">
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "data-sources" ? "bg-[#1a1a1a] text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-[#1a1a1a]"}`}
                    onClick={() => setActiveSidebarItem("data-sources")}
                  >
                    <Database className="w-3.5 h-3.5" />
                    Data Sources
                  </div>
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "ai-economists" ? "bg-[#1a1a1a] text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-[#1a1a1a]"}`}
                    onClick={() => setActiveSidebarItem("ai-economists")}
                  >
                    <Bot className="w-3.5 h-3.5" />
                    AI Agents
                  </div>
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "health-checks" ? "bg-[#1a1a1a] text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-[#1a1a1a]"}`}
                    onClick={() => setActiveSidebarItem("health-checks")}
                  >
                    <Zap className="w-3.5 h-3.5" />
                    Health Checks
                  </div>
                </nav>

                <Separator className="bg-[#1a1a1a]" />

                <nav className="space-y-0.5">
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "events-log" ? "bg-[#1a1a1a] text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-[#1a1a1a]"}`}
                    onClick={() => setActiveSidebarItem("events-log")}
                  >
                    <ClipboardList className="w-3.5 h-3.5" />
                    Events Log
                  </div>
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "billing" ? "bg-[#1a1a1a] text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-[#1a1a1a]"}`}
                    onClick={() => setActiveSidebarItem("billing")}
                  >
                    <CreditCardIcon className="w-3.5 h-3.5" />
                    Billing & Invoices
                  </div>
                </nav>

                <Separator className="bg-[#1a1a1a]" />

                <nav className="space-y-0.5">
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "compliance" ? "bg-[#1a1a1a] text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-[#1a1a1a]"}`}
                    onClick={() => setActiveSidebarItem("compliance")}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    Compliance Reports
                  </div>
                  <div
                    className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${activeSidebarItem === "contact" ? "bg-[#1a1a1a] text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-[#1a1a1a]"}`}
                    onClick={() => setActiveSidebarItem("contact")}
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    Contact Us
                  </div>
                </nav>
              </div>
            </aside>
          )}

          {/* Main Content */}
          <main className={`flex-1 p-5 max-w-3xl ${activeTab === "agents" ? "mx-auto" : ""}`}>
            {activeTab === "agents" && (
              <div className="max-w-xl mx-auto">
                <div className="flex flex-col items-center justify-center min-h-[45vh] space-y-5">
                  <div className="w-full space-y-3">
                    <div className="relative">
                      <textarea
                        placeholder="Is my pricing behaviour competitive or collusive?"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        className="w-full h-28 bg-[#1a1a1a] rounded-lg text-[#f9fafb] placeholder-[#71717a] pr-16 px-4 py-4 text-xs resize-none focus:outline-none shadow-[0_1px_0_rgba(0,0,0,0.20)] border border-[#2a2a2a]/50"
                        rows={5}
                      />
                      {/* Blinking cursor overlay - only shows when empty */}
                      {inputValue === "" && (
                        <div
                          className="absolute left-4 top-4 text-[#f9fafb] text-xs"
                          style={{
                            animation: "blink 1s infinite",
                            display: "inline-block",
                          }}
                        >
                          |
                        </div>
                      )}
                      {/* Model selector - bottom left */}
                      <div className="absolute left-3 bottom-3 flex items-center gap-1.5">
                        <Bot className="w-3.5 h-3.5 text-[#71717a]" />
                        <select
                          value={selectedAgent}
                          onChange={(e) => setSelectedAgent(e.target.value)}
                          className="bg-transparent text-[10px] text-[#71717a] font-medium border-none outline-none cursor-pointer hover:text-[#a1a1aa]"
                        >
                          <option value="Associate">Associate</option>
                          <option value="Legal">Legal</option>
                          <option value="Economist">Economist</option>
                          <option value="Statistician">Statistician</option>
                        </select>
                    </div>

                      {/* Action buttons - bottom right */}
                      <div className="absolute right-3 bottom-3 flex gap-1.5">
                        <div
                          className="h-6 w-6 flex items-center justify-center cursor-pointer"
                          onClick={() => {
                            // Simulate file upload
                            setUploadedFiles((prev) => [...prev, "pricing_data.csv"])
                          }}
                        >
                          <CloudUpload className="w-4 h-4 text-[#71717a] hover:text-[#a1a1aa]" />
                        </div>
                        <div className="h-6 w-6 flex items-center justify-center">
                          <Send className="w-4 h-4 text-[#71717a] hover:text-[#a1a1aa]" />
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4 mt-8">
                      <p className="text-[10px] text-[#a1a1aa] text-center">Try these examples to get started</p>

                      <div className="flex flex-wrap gap-2 justify-center">
                        <button className="rounded-full px-3 py-1 text-[10px] border border-[#2a2a2a] bg-[#1a1a1a] hover:bg-[#2a2a2a] text-[#a1a1aa] hover:text-[#f9fafb] flex items-center gap-1.5">
                          <Zap className="w-2.5 h-2.5" />
                          Analyze pricing patterns
                        </button>
                        <button className="rounded-full px-3 py-1 text-[10px] border border-[#2a2a2a] bg-[#1a1a1a] hover:bg-[#2a2a2a] text-[#a1a1aa] hover:text-[#f9fafb] flex items-center gap-1.5">
                          <ShieldCheck className="w-2.5 h-2.5" />
                          Check compliance status
                        </button>
                        <button className="rounded-full px-3 py-1 text-[10px] border border-[#2a2a2a] bg-[#1a1a1a] hover:bg-[#2a2a2a] text-[#a1a1aa] hover:text-[#f9fafb] flex items-center gap-1.5">
                          <FileText className="w-2.5 h-2.5" />
                          Generate report
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {activeTab === "dashboard" && (
              /* Dashboard View */
              <>
                {activeSidebarItem === "overview" && (
              <div className="space-y-3 max-w-2xl">
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-4">
                        <div className="grid grid-cols-2 gap-6">
                          <div className="rounded-lg bg-[#1a1a1a] shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                            <div>
                        <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Enterprise Plan</h2>
                              <p className="text-xs text-[#a1a1aa] mb-3 leading-relaxed">
                                Live monitoring with compliance tracking
                        </p>
                            </div>
                            <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-[#1a1a1a] text-[#a1a1aa] hover:text-[#f9fafb] self-start">
                          Manage Subscription
                        </button>
                      </div>
                          <div className="rounded-lg bg-[#1e1e1e] shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                            <div>
                          <div className="text-xs font-bold text-[#f9fafb] mb-1">$0 / $6k</div>
                          <p className="text-xs text-[#a1a1aa] mb-2">Usage-Based Spending this Month</p>
                            </div>
                            <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-[#1a1a1a] text-[#a1a1aa] hover:text-[#f9fafb] self-start">
                            Edit Limit
                          </button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
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
                            onClick={() => setSelectedTimeframe("YTD")}
                                    className={`text-xs px-2 py-1 ${selectedTimeframe === "YTD" ? "text-[#f9fafb] bg-[#3a3a3a] rounded" : "text-[#a1a1aa] hover:text-[#f9fafb]"}`}
                          >
                            YTD
                          </button>
                        </div>
                              </>
                      )}
                          </div>
                    </div>

                    <div className="mb-4">
                      <h3 className="text-xs font-medium text-[#f9fafb] mb-3">Your Coordination Risk</h3>
                          <div className="grid grid-cols-2 gap-6 mb-10">
                            <div className="rounded-lg bg-[#212121] shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                          <div className="text-xl font-bold text-[#f9fafb]">14 out of 100</div>
                              <div className="text-xs text-[#a7f3d0]">Low Risk</div>
                        </div>
                            <div className="rounded-lg bg-[#212121]/40 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                              <div className="text-xl font-bold text-[#f9fafb]">{21 + 21 + 26 + 16}%</div>
                              <div className="text-xs text-[#a1a1aa]">Weekly Price Leader</div>
                        </div>
                      </div>

                          <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={currentData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
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
                                    value: "SA Bank CDS Spread %",
                                angle: -90,
                                position: "insideLeft",
                                style: { textAnchor: "middle", fill: "#a1a1aa", fontSize: 10 },
                              }}
                            />
                                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" opacity={0.75} />
                            <Tooltip
                                  cursor={false}
                              content={({ active, payload, label }) => {
                                if (active && payload && payload.length) {
                                      // Market share data for each bank
                                      const marketShare = {
                                        FNB: 21,
                                        ABSA: 21,
                                        "Standard Bank": 26,
                                        Nedbank: 16,
                                      }

                                  return (
                                        <div className="bg-black border border-[#1a1a1a] rounded-lg p-3 shadow-2xl shadow-black/50">
                                          <p className="text-[#a1a1aa] text-[10px] mb-1.5">{label}</p>
                                      {payload.map((entry, index) => (
                                            <div key={index} className="flex items-center gap-2 text-[9px]">
                                          <div 
                                            className="w-2 h-2 rounded-full" 
                                            style={{ backgroundColor: entry.color }}
                                          />
                                              <span className="text-[#f9fafb] font-semibold">
                                                {entry.name}: <span className="font-bold">{entry.value} bps</span> |{" "}
                                                <span className="text-[#a1a1aa]">
                                                  {marketShare[entry.name as keyof typeof marketShare]}% share
                                                </span>
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
                              dataKey="fnb"
                              stroke="#60a5fa"
                              strokeWidth={2}
                              dot={{ fill: "#60a5fa", strokeWidth: 2, r: 3 }}
                              activeDot={{ r: 4, fill: "#60a5fa" }}
                              name="FNB"
                            />
                            <Line
                              type="monotone"
                              dataKey="absa"
                              stroke="#a1a1aa"
                              strokeWidth={1.5}
                              dot={{ fill: "#a1a1aa", strokeWidth: 1.5, r: 2 }}
                              activeDot={{ r: 3, fill: "#a1a1aa" }}
                              name="ABSA"
                            />
                            <Line
                              type="monotone"
                              dataKey="standard"
                              stroke="#71717a"
                              strokeWidth={1.5}
                              dot={{ fill: "#71717a", strokeWidth: 1.5, r: 2 }}
                              activeDot={{ r: 3, fill: "#71717a" }}
                              name="Standard Bank"
                            />
                            <Line
                              type="monotone"
                              dataKey="nedbank"
                              stroke="#52525b"
                              strokeWidth={1.5}
                              dot={{ fill: "#52525b", strokeWidth: 1.5, r: 2 }}
                              activeDot={{ r: 3, fill: "#52525b" }}
                              name="Nedbank"
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                {/* Metrics tile: Price Stability, Price Synchronization, Environmental Sensitivity */}
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-0">
                    {/* Price Stability */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <TrendingUp className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Price Stability</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  How steady your prices are compared to competitors
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
                    
                    {/* Price Synchronization */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <GitBranch className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Price Synchronization</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  How much your prices move together with other banks
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">1m ago • 32s</div>
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
                    
                    {/* Environmental Sensitivity */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <Activity className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Environmental Sensitivity</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  How well you respond to market changes and economic events
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
                  </CardContent>
                </Card>

                {/* Combined tile: Market Data Feed, Regulatory Notices */}
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-0">
                    {/* Market Data Feed */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <BarChart3 className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Market Data Feed</div>
                            <div className="text-[10px] text-[#a1a1aa]">
                              Real-time market data and price information
                            </div>
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                        >
                          Connect
                        </Button>
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
                              Important updates and compliance notifications
                            </div>
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                        >
                          Connect
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Sixth tile: Assign Reviewers */}
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-4 text-center">
                    <h3 className="text-[#f9fafb] font-medium mb-1.5 text-xs">Assign Reviewers</h3>
                    <p className="text-[10px] text-[#a1a1aa] mb-2.5">
                      Ensure independent oversight of monitoring outputs.
                    </p>
                    <Button
                      variant="outline"
                      className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
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
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-0">
                    {/* Section Header */}
                    <div className="px-4 py-3 border-b border-[#2a2a2a]">
                      <h2 className="text-sm font-medium text-[#f9fafb]">Pricing Analysis Settings</h2>
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
                                    Enable automatic detection of significant market changes
                                  </div>
                                </div>
                              </div>
                        </div>
                        <div className="ml-4">
                          <button 
                            onClick={() => setAutoDetectMarketChanges(!autoDetectMarketChanges)}
                            className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                  autoDetectMarketChanges ? "bg-[#22c55e]" : "bg-[#374151]"
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
                            <div className="text-xs font-medium text-[#f9fafb]">Change Threshold</div>
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                    Minimum change required to trigger analysis
                          </div>
                        </div>
                              </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={changeThreshold}
                            onChange={(e) => setChangeThreshold(e.target.value)}
                                className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-md px-3 py-1.5 text-xs text-[#f9fafb] cursor-pointer hover:bg-[#2a2a2a] focus:border-[#60a5fa] focus:outline-none focus:ring-1 focus:ring-[#60a5fa] transition-colors duration-200 appearance-none pr-8"
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
                                    Statistical confidence required for alerts
                          </div>
                        </div>
                              </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={confidenceLevel}
                            onChange={(e) => setConfidenceLevel(e.target.value)}
                                className="w-20 h-8 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-xs text-[#f9fafb] text-center appearance-none cursor-pointer hover:bg-[#2a2a2a] transition-colors duration-200 pr-6"
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
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
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
                                    Real-time analysis and risk assessment
                          </div>
                                </div>
                              </div>
                        </div>
                        <div className="ml-4">
                          <button 
                            onClick={() => setEnableLiveMonitoring(!enableLiveMonitoring)}
                            className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                  enableLiveMonitoring ? "bg-[#22c55e]" : "bg-[#374151]"
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
                                  <div className="text-[10px] text-[#a1a1aa] mt-0.5">How often to run analysis</div>
                          </div>
                        </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={updateFrequency}
                            onChange={(e) => setUpdateFrequency(e.target.value)}
                                className="w-20 h-8 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-xs text-[#f9fafb] text-center appearance-none cursor-pointer hover:bg-[#2a2a2a] transition-colors duration-200 pr-6"
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
                                    How sensitive the detection should be
                          </div>
                        </div>
                              </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={sensitivityLevel}
                            onChange={(e) => setSensitivityLevel(e.target.value)}
                                className="w-20 h-8 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-xs text-[#f9fafb] text-center appearance-none cursor-pointer hover:bg-[#2a2a2a] transition-colors duration-200 pr-6"
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
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
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
                                    Validate data accuracy and consistency
                          </div>
                                </div>
                              </div>
                        </div>
                        <div className="ml-4">
                          <button 
                            onClick={() => setCheckDataQuality(!checkDataQuality)}
                            className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${
                                  checkDataQuality ? "bg-[#22c55e]" : "bg-[#374151]"
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
                                    Maximum age before switching to backup
                          </div>
                        </div>
                              </div>
                            </div>
                            <div className="ml-4 relative">
                              <select
                            value={maxDataAge}
                            onChange={(e) => setMaxDataAge(e.target.value)}
                                className="w-20 h-8 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-xs text-[#f9fafb] text-center appearance-none cursor-pointer hover:bg-[#2a2a2a] transition-colors duration-200 pr-6"
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
                  <div className="space-y-3 max-w-2xl">
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-0">
                        {/* Section Header */}
                        <div className="px-4 py-3 border-b border-[#2a2a2a]">
                          <h2 className="text-sm font-medium text-[#f9fafb]">Connect Your Data</h2>
                        </div>

                        {/* File Upload */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Upload className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Upload Files</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  CSV, JSON, Parquet files for batch analysis
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">
                                  Supports up to 100MB • Auto-validation enabled
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                            >
                              Connect
                            </Button>
                          </div>
                        </div>

                        {/* Separator */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* API Integration */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Database className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">API Integration</div>
                                <div className="text-[10px] text-[#a1a1aa]">Real-time pricing feeds and webhooks</div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">
                                  REST & GraphQL • Rate limiting included
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                            >
                              Connect
                            </Button>
                          </div>
                        </div>

                        {/* Separator */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* Database Connection */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Server className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Database Connection</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  PostgreSQL, MongoDB, and other databases
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">
                                  SSL encryption • Connection pooling
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                            >
                              Connect
                            </Button>
                          </div>
                        </div>

                        {/* Separator */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* Cloud Storage */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Cloud className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Cloud Storage</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  S3, Azure Blob, and other cloud providers
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">Auto-sync • Multi-region support</div>
                              </div>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                            >
                              Connect
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* API Keys Section */}
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-4">
                        <h3 className="text-xs font-medium text-[#f9fafb] mb-3">API Keys</h3>
                        <div className="space-y-2">
                          <button className="w-full text-left p-3 bg-[#212121] hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors">
                            <div className="font-medium">Generate new API key</div>
                            <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                              Create secure access tokens for data integration
                            </div>
                          </button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
                {/* AI Economists Page */}
                {activeSidebarItem === "ai-economists" && (
                  <div className="space-y-3 max-w-2xl">
                    {/* Multiple Agent Cards */}
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-0">
                        {/* Section Header */}
                        <div className="px-4 py-3 border-b border-[#2a2a2a]">
                          <h2 className="text-sm font-medium text-[#f9fafb]">Specialized Agents</h2>
                        </div>

                        {/* US Market Compliance Agent */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <Scale className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">US Market Compliance Agent</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Sherman Act analysis and antitrust compliance
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">
                                  1,247 scenarios analyzed • 96% accuracy
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                            >
                              Chat
                            </Button>
                          </div>
                        </div>

                        {/* Separator */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* EU Competition Agent */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <FileText className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">EU Competition Agent</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Article 101 interpretation and GDPR compliance
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">
                                  892 cases processed • 94% accuracy
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                            >
                              Chat
                            </Button>
                          </div>
                        </div>

                        {/* Separator */}
                        <div
                          className="border-t border-[#2a2a2a]/70 border-opacity-70"
                          style={{ borderTopWidth: "0.5px" }}
                        ></div>

                        {/* Surge Pricing Analyst */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <TrendingUp className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Surge Pricing Analyst</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Dynamic pricing and demand-based algorithms
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">
                                  3,156 surge events analyzed • 98% accuracy
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                            >
                              Chat
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Smart Prompt Suggestions */}
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-4">
                        <h3 className="text-xs font-medium text-[#f9fafb] mb-3">Quick Analysis</h3>
                        <div className="space-y-2">
                          <button className="w-full text-left p-3 bg-[#212121] hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors flex items-center justify-between">
                            <div>
                              <div className="font-medium">Analyze surge pricing compliance</div>
                              <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                Review dynamic pricing against competition law
                              </div>
                            </div>
                            <SquareChevronRight className="w-4 h-4 text-[#a1a1aa]" />
                          </button>
                          <button className="w-full text-left p-3 bg-[#212121] hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors flex items-center justify-between">
                            <div>
                              <div className="font-medium">Generate Q3 compliance report</div>
                              <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                Comprehensive quarterly analysis and documentation
                              </div>
                            </div>
                            <SquareChevronRight className="w-4 h-4 text-[#a1a1aa]" />
                          </button>
                          <button className="w-full text-left p-3 bg-[#212121] hover:bg-[#2a2a2a] rounded-lg text-xs text-[#f9fafb] transition-colors flex items-center justify-between">
                            <div>
                              <div className="font-medium">Cross-market coordination assessment</div>
                              <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                                Multi-jurisdictional pricing strategy review
                              </div>
                            </div>
                            <SquareChevronRight className="w-4 h-4 text-[#a1a1aa]" />
                          </button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
                {/* Health Checks Page */}
                {activeSidebarItem === "health-checks" && (
                  <div className="space-y-3 max-w-2xl">
                    {/* Notification banner */}
                    <div className="bg-[#2a1f0a] border border-[#3d2914] rounded-lg p-3">
                      <p className="text-xs text-[#f59e0b]">
                        System health monitoring active. Upgrade to RBB Pro for advanced diagnostics and alerts.
                      </p>
                    </div>

                    {/* Main Health Checks card */}
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-4">
                        {/* Header */}
                        <div className="mb-4">
                          <div className="flex items-center gap-2 mb-1">
                            <h2 className="text-sm font-medium text-[#f9fafb]">System Health</h2>
                            <span className="text-xs text-[#22c55e] bg-[#0f1f0f] px-2 py-0.5 rounded">Active</span>
                          </div>
                          <p className="text-xs text-[#a1a1aa]">
                            Automatically monitor system performance and compliance metrics
                          </p>
                        </div>

                        {/* Analytics section */}
                        <div className="mb-6 text-center py-8">
                          <h3 className="text-xs font-medium text-[#f9fafb] mb-1">No Health Analytics Available Yet</h3>
                          <p className="text-xs text-[#71717a]">
                            Continue using Health Checks to view system analytics and trends
                          </p>
                        </div>

                        {/* Configuration sections */}
                        <div className="space-y-0">
                          {/* Database Connections */}
                          <div
                            className="flex items-center justify-between py-3 border-t border-[#2a2a2a]/70"
                            style={{ borderTopWidth: "0.5px" }}
                          >
                            <div>
                              <h4 className="text-xs font-medium text-[#f9fafb] mb-0.5">Database Connections</h4>
                              <p className="text-xs text-[#71717a]">Monitor database connectivity and performance</p>
                            </div>
                            <Button
                              variant="outline"
                              className="border-[#2a2a2a] text-[#a1a1aa] bg-transparent hover:bg-[#1e1e1e] text-xs h-6 px-3"
                            >
                              Configure
                            </Button>
                          </div>

                          {/* API Health Monitoring */}
                          <div
                            className="flex items-center justify-between py-3 border-t border-[#2a2a2a]/70"
                            style={{ borderTopWidth: "0.5px" }}
                          >
                            <div>
                              <h4 className="text-xs font-medium text-[#f9fafb] mb-0.5">API Health Monitoring</h4>
                              <p className="text-xs text-[#71717a]">
                                Get unlimited health checks with RBB Pro. Start your 14-day free trial
                              </p>
                            </div>
                            <Button
                              variant="outline"
                              className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-xs h-6 px-3"
                            >
                              Upgrade
                            </Button>
                          </div>

                          {/* Alert on Critical Issues */}
                          <div
                            className="flex items-center justify-between py-3 border-t border-[#2a2a2a]/70"
                            style={{ borderTopWidth: "0.5px" }}
                          >
                            <div>
                              <h4 className="text-xs font-medium text-[#f9fafb] mb-0.5">Alert on Critical Issues</h4>
                              <p className="text-xs text-[#71717a]">
                                Only send alerts when critical system issues are detected
                              </p>
                            </div>
                            <div className="w-8 h-4 bg-[#2563eb] rounded-full relative cursor-pointer">
                              <div className="w-3 h-3 bg-white rounded-full absolute top-0.5 right-0.5"></div>
                            </div>
                          </div>

                          {/* Auto-Restart Services */}
                          <div
                            className="flex items-center justify-between py-3 border-t border-[#2a2a2a]/70"
                            style={{ borderTopWidth: "0.5px" }}
                          >
                            <div>
                              <h4 className="text-xs font-medium text-[#f9fafb] mb-0.5">Auto-Restart Services</h4>
                              <p className="text-xs text-[#71717a]">
                                Automatically restart services when health checks fail
                              </p>
                            </div>
                            <div className="w-8 h-4 bg-[#2563eb] rounded-full relative cursor-pointer">
                              <div className="w-3 h-3 bg-white rounded-full absolute top-0.5 right-0.5"></div>
                            </div>
                          </div>

                          {/* Monitor Compliance Status */}
                          <div
                            className="flex items-center justify-between py-3 border-t border-[#2a2a2a]/70"
                            style={{ borderTopWidth: "0.5px" }}
                          >
                            <div>
                              <h4 className="text-xs font-medium text-[#f9fafb] mb-0.5">Monitor Compliance Status</h4>
                              <p className="text-xs text-[#71717a]">
                                Track regulatory compliance and generate automated reports
                              </p>
                            </div>
                            <div className="w-8 h-4 bg-[#374151] rounded-full relative cursor-pointer">
                              <div className="w-3 h-3 bg-white rounded-full absolute top-0.5 left-0.5"></div>
                            </div>
                          </div>
                        </div>

                        {/* Footer */}
                        <div
                          className="flex items-center justify-between pt-4 border-t border-[#2a2a2a]/70 mt-4"
                          style={{ borderTopWidth: "0.5px" }}
                        >
                          <span className="text-xs text-[#71717a]">rbb.economics</span>
                          <div className="flex items-center gap-1 text-xs text-[#71717a]">
                            <span>12 Services</span>
                            <span>•</span>
                            <span>8 Healthy</span>
                            <ChevronRight className="w-3 h-3" />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
                {/* Events Log Page */}
                {activeSidebarItem === "events-log" && (
                  <div className="space-y-3 max-w-2xl">
                    {/* First shell tile with left and right containers */}
                    <div className="bg-transparent">
                      <div className="flex items-center justify-between mb-4">
                        {/* Left Container - Date Range and Time Tabs */}
                        <div className="flex items-center gap-4">
                          {/* Date Range Button */}
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs bg-transparent border-[#2a2a2a] text-[#f9fafb] hover:bg-[#1a1a1a]"
                          >
                            Jan 01 - Sep 05
                            <ChevronDown className="w-3 h-3 ml-1" />
                          </Button>

                          {/* Time Tabs */}
                          <div className="flex gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-[#1a1a1a] hover:text-[#f9fafb]"
                            >
                              30d
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-[#1a1a1a] hover:text-[#f9fafb]"
                            >
                              6m
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-[#1a1a1a] hover:text-[#f9fafb]"
                            >
                              1y
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-[#1a1a1a] border-[#2a2a2a] text-[#f9fafb]"
                            >
                              YTD
                            </Button>
                          </div>
                        </div>

                        {/* Right Container - Export CSV Button */}
                        <div className="flex justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs bg-transparent border-[#2a2a2a] text-[#f9fafb] hover:bg-[#1a1a1a]"
                          >
                            <Download className="w-3 h-3 mr-1" />
                            Export CSV
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Option 3: Text Labels Metrics Tile */}
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-0">
                        {/* Title Section */}
                        <div className="px-4 py-3 border-b border-[#2a2a2a]">
                          <h2 className="text-sm font-medium text-[#f9fafb]">All Events</h2>
                        </div>

                        {/* Event Status 1 */}
                        <div className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                              <CalendarCheck2 className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">ZAR depreciates 1.9%</div>
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Broad CDS widening; sensitivity ↑ to 84
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">2m ago • 45s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1.5">
                                <div className="text-[#f9fafb] font-bold text-sm">66 out of 100</div>
                              </div>
                              <div className="text-[10px] text-[#fca5a5]">High Risk</div>
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
                              <CalendarCheck2 className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">SARB guidance unchanged</div>
                                <div className="text-[10px] text-[#a1a1aa]">No regime break detected</div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">1m ago • 32s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1.5">
                                <div className="text-[#f9fafb] font-bold text-sm">43 out of 100</div>
                              </div>
                              <div className="text-[10px] text-[#a7f3d0]">Low Risk</div>
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
                              <CalendarCheck2 className="w-4 h-4 text-[#a1a1aa]" />
                              <div>
                                <div className="text-[#f9fafb] font-medium text-xs">Sovereign outlook stable</div>
                                <div className="text-[10px] text-[#a1a1aa]">Idiosyncratic responses across banks</div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">30s ago • 18s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center gap-1.5">
                                <div className="text-[#f9fafb] font-bold text-sm">18 out of 100</div>
                              </div>
                              <div className="text-[10px] text-[#fbbf24]">Medium Risk</div>
                            </div>
                          </div>
                        </div>

                        {/* Pagination Footer */}
                        <div className="px-4 py-3 border-t border-[#2a2a2a]">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4 text-[10px] text-[#a1a1aa]">
                              <span>Showing 1 - 3 of 3 events</span>
                              <div className="flex items-center gap-2">
                                <span>Rows per page:</span>
                                <select className="bg-transparent border border-[#2a2a2a] rounded px-2 py-1 text-[#f9fafb] text-[10px]">
                                  <option value="100">100</option>
                                </select>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 text-[10px] text-[#a1a1aa]">
                              <span>Page 1 of 1</span>
                              <div className="flex gap-1">
                                <button
                                  className="p-1 text-[#a1a1aa] hover:text-[#f9fafb] disabled:opacity-50"
                                  disabled
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                                    />
                                  </svg>
                                </button>
                                <button
                                  className="p-1 text-[#a1a1aa] hover:text-[#f9fafb] disabled:opacity-50"
                                  disabled
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M15 19l-7-7 7-7"
                                    />
                                  </svg>
                                </button>
                                <button
                                  className="p-1 text-[#a1a1aa] hover:text-[#f9fafb] disabled:opacity-50"
                                  disabled
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M9 5l7 7-7 7"
                                    />
                                  </svg>
                                </button>
                                <button
                                  className="p-1 text-[#a1a1aa] hover:text-[#f9fafb] disabled:opacity-50"
                                  disabled
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M13 5l7 7-7 7M5 5l7 7-7 7"
                                    />
                                  </svg>
                                </button>
                              </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
                )}

                {/* Billing Page */}
                {activeSidebarItem === "billing" && (
                  <div className="space-y-6 max-w-4xl">
                    {/* Enterprise Plan Summary */}
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-6">
                        <div className="mb-6">
                          <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Enterprise Plan Summary</h2>
                          <p className="text-xs text-[#a1a1aa]">29 Aug 2025 - 29 Sept 2025</p>
                        </div>

                        <div className="overflow-hidden">
                          <table className="w-full">
                            <thead>
                              <tr className="border-b border-[#2a2a2a]/70">
                                <th className="text-left text-xs text-[#a1a1aa] font-medium pb-3">Item</th>
                                <th className="text-right text-xs text-[#a1a1aa] font-medium pb-3">Quantity</th>
                                <th className="text-right text-xs text-[#a1a1aa] font-medium pb-3">Cost</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr className="border-b border-[#2a2a2a]/70">
                                <td className="py-3">
                                  <div className="text-xs text-[#f9fafb] font-medium">Included in Enterprise</div>
                                  <div className="text-xs text-[#a1a1aa]">
                                    Compliance Reports - Unlimited until 29 Sept 2025
                                  </div>
                                </td>
                                <td className="text-right text-xs text-[#f9fafb] py-3">2.4M assessments</td>
                                <td className="text-right text-xs text-[#f9fafb] py-3">Free</td>
                              </tr>
                              <tr>
                                <td className="py-3">
                                  <div className="text-xs text-[#f9fafb] font-medium">Total</div>
                                </td>
                                <td className="text-right text-xs text-[#f9fafb] py-3">2.4M</td>
                                <td className="text-right text-xs text-[#f9fafb] py-3">
                                  <span className="line-through text-[#a1a1aa]">US$2,400.00</span> included
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>

                        <div className="mt-4 text-xs text-[#a1a1aa]">
                          * Your plan has unlimited Compliance Reports until 29 Sept 2025.{" "}
                          <span className="text-[#60a5fa] cursor-pointer">Learn more</span>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Invoice Section */}
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                      <CardContent className="p-6">
                        <div className="flex items-center justify-between mb-6">
                          <select className="bg-[#1e1e1e] border border-[#2a2a2a] rounded-md px-3 py-1.5 text-xs text-[#f9fafb] focus:outline-none focus:ring-1 focus:ring-[#60a5fa]">
                            <option>September 2025</option>
                            <option>August 2025</option>
                            <option>July 2025</option>
                          </select>
                          <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-[#1a1a1a] text-[#a1a1aa] hover:text-[#f9fafb]">
                            Manage Subscription
                          </button>
                        </div>

                        <div className="mb-4">
                          <h3 className="text-sm text-[#f9fafb] mb-1">September 2025 • Upcoming Invoice</h3>
                          <div className="text-lg font-medium text-[#f9fafb]">
                            US$0.00 <span className="text-sm text-[#a1a1aa] line-through">US$6,000.00</span>
                          </div>
                        </div>

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

                        <div className="mt-6 text-center text-xs text-[#a1a1aa]">
                          No invoices found for September 2025
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* Compliance Reports Page */}
                {activeSidebarItem === "compliance" && (
                  <div className="space-y-3 max-w-2xl">
                    {/* First shell tile with left and right containers */}
                    <div className="bg-transparent">
                      <div className="flex items-center justify-between mb-4">
                        {/* Left Container - Date Range and Time Tabs */}
                        <div className="flex items-center gap-4">
                          {/* Date Range Button */}
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs bg-transparent border-[#2a2a2a] text-[#f9fafb] hover:bg-[#1a1a1a]"
                          >
                            Jan 01 - Sep 05
                            <ChevronDown className="w-3 h-3 ml-1" />
                          </Button>

                          {/* Time Tabs */}
                          <div className="flex gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-[#1a1a1a] hover:text-[#f9fafb]"
                            >
                              30d
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-[#1a1a1a] hover:text-[#f9fafb]"
                            >
                              6m
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-transparent border-[#2a2a2a] text-[#a1a1aa] hover:bg-[#1a1a1a] hover:text-[#f9fafb]"
                            >
                              1y
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-xs bg-[#1a1a1a] border-[#2a2a2a] text-[#f9fafb]"
                            >
                              YTD
                            </Button>
                          </div>
                        </div>

                        {/* Right Container - Export ZIP Button */}
                        <div className="flex justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs bg-transparent border-[#2a2a2a] text-[#f9fafb] hover:bg-[#1a1a1a]"
                          >
                            <Download className="w-3 h-3 mr-1" />
                            Export ZIP
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Option 3: Text Labels Metrics Tile */}
                    <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
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
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Healthy: 3 instances of competitive adaptation to regime breaks
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">2m ago • 45s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
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
                                <div className="text-[10px] text-[#a1a1aa]">
                                  Spread Dispersion of 17 bps, ↑ +15% in 24 hrs
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">1m ago • 32s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
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
                                <div className="text-[10px] text-[#a1a1aa]">
                                  96.8% statistical confidence over 18-month view
                                </div>
                                <div className="text-[9px] text-[#a1a1aa] mt-0.5">30s ago • 18s</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                className="border-[#2563eb] text-[#ffffff] bg-[#2563eb] hover:bg-[#1d4ed8] text-[10px] h-6"
                              >
                                Download
                              </Button>
                            </div>
                          </div>
                        </div>

                        {/* Pagination Footer */}
                        <div className="px-4 py-3 border-t border-[#2a2a2a]">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4 text-[10px] text-[#a1a1aa]">
                              <span>Showing 1 - 3 of 3 events</span>
                              <div className="flex items-center gap-2">
                                <span>Rows per page:</span>
                                <select className="bg-transparent border border-[#2a2a2a] rounded px-2 py-1 text-[#f9fafb] text-[10px]">
                                  <option value="100">100</option>
                                </select>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 text-[10px] text-[#a1a1aa]">
                              <span>Page 1 of 1</span>
                              <div className="flex gap-1">
                                <button
                                  className="p-1 text-[#a1a1aa] hover:text-[#f9fafb] disabled:opacity-50"
                                  disabled
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                                    />
                                  </svg>
                                </button>
                                <button
                                  className="p-1 text-[#a1a1aa] hover:text-[#f9fafb] disabled:opacity-50"
                                  disabled
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M15 19l-7-7 7-7"
                                    />
                                  </svg>
                                </button>
                                <button
                                  className="p-1 text-[#a1a1aa] hover:text-[#f9fafb] disabled:opacity-50"
                                  disabled
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M9 5l7 7-7 7"
                                    />
                                  </svg>
                                </button>
                                <button
                                  className="p-1 text-[#a1a1aa] hover:text-[#f9fafb] disabled:opacity-50"
                                  disabled
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M13 5l7 7-7 7M5 5l7 7-7 7"
                                    />
                                  </svg>
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* Contact Page */}
                {activeSidebarItem === "contact" && renderShellTiles("Contact Us")}
              </>
            )}
          </main>
        </div>
      </div>

      <style jsx>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}
