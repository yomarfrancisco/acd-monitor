"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts"
import { CalendarIcon } from "lucide-react"
import {
  MessageSquare,
  BarChart3,
  Settings,
  Users,
  Zap,
  FileText,
  Search,
  Github,
  Slack,
  Link,
  User,
  TrendingUp,
  GitBranch,
  Activity,
  Database,
  Cpu,
  ClipboardList,
  CreditCard,
  Bot,
  Cloud,
  Send,
  CloudUpload,
  Package,
  ChevronDown,
} from "lucide-react"

// Different data sets for different time periods
const analyticsData30d = [
  { date: "Aug 06", fnb: 100, absa: 95, standard: 105, nedbank: 98 },
  { date: "Aug 13", fnb: 150, absa: 145, standard: 155, nedbank: 148 },
  { date: "Aug 20", fnb: 200, absa: 190, standard: 210, nedbank: 195 },
  { date: "Aug 27", fnb: 250, absa: 240, standard: 260, nedbank: 245 },
  { date: "Sep 03", fnb: 300, absa: 290, standard: 310, nedbank: 295 },
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

// Fresh deployment commit - rollback to working state
export default function CursorDashboard() {
  const [activeTab, setActiveTab] = useState<"agents" | "dashboard" | "events">("agents")
  const [selectedTimeframe, setSelectedTimeframe] = useState<"30d" | "6m" | "1y" | "YTD">("YTD")
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)
  const [selectedDate, setSelectedDate] = useState<{from: Date | undefined, to?: Date | undefined} | undefined>({
    from: new Date(),
    to: new Date()
  })
  const [isClient, setIsClient] = useState(false)
  const [inputValue, setInputValue] = useState("")

  useEffect(() => {
    setIsClient(true)
  }, [])

  // Close calendar when switching to agents tab
  const handleTabChange = (tab: "agents" | "dashboard" | "events") => {
    setActiveTab(tab)
    if (tab === "agents") {
      setIsCalendarOpen(false)
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
      case "YTD":
        return analyticsDataYTD
      default:
        return analyticsDataYTD
    }
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
              className="h-36 w-auto opacity-90 hover:opacity-100 transition-opacity"
            />
          </div>

          <nav className="flex gap-5 absolute left-1/2 transform -translate-x-1/2">
            <button
              onClick={() => handleTabChange("agents")}
              className={`px-2.5 py-1 text-xs font-medium ${
                activeTab === "agents"
                  ? "text-[#f9fafb] border-b-2 border-[#f9fafb]"
                  : "text-[#a1a1aa] hover:text-[#f9fafb]"
              }`}
            >
              Agents
            </button>
            <button
              onClick={() => handleTabChange("dashboard")}
              className={`px-2.5 py-1 text-xs font-medium ${
                activeTab === "dashboard"
                  ? "text-[#f9fafb] border-b-2 border-[#f9fafb]"
                  : "text-[#a1a1aa] hover:text-[#f9fafb]"
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => handleTabChange("events")}
              className={`px-2.5 py-1 text-xs font-medium ${
                activeTab === "events"
                  ? "text-[#f9fafb] border-b-2 border-[#f9fafb]"
                  : "text-[#a1a1aa] hover:text-[#f9fafb]"
              }`}
            >
              Events Log
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

                  <div className="bg-[#1a1a1a] rounded-md p-1.5 mb-2.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-[#f9fafb]">
                      <User className="w-3.5 h-3.5" />
                      Overview
                    </div>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="flex items-center gap-2 text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                      <Settings className="w-3.5 h-3.5" />
                      Configuration
                    </div>
                  </div>
                </div>

                <Separator className="bg-[#1a1a1a]" />

                {/* Navigation */}
                <nav className="space-y-0.5">
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <Database className="w-3.5 h-3.5" />
                    Data Sources
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <Bot className="w-3.5 h-3.5" />
                    AI Economists
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <Zap className="w-3.5 h-3.5" />
                    Health Checks
                  </div>
                </nav>

                <Separator className="bg-[#1a1a1a]" />

                <nav className="space-y-0.5">
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                            <ClipboardList className="w-3.5 h-3.5" />
                            Events Log
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <CreditCard className="w-3.5 h-3.5" />
                    Billing & Invoices
                  </div>
                </nav>

                <Separator className="bg-[#1a1a1a]" />

                <nav className="space-y-0.5">
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <FileText className="w-3.5 h-3.5" />
                    Compliance Reports
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
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
              /* Agents View */
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
                          <div className="absolute left-4 top-4 text-[#f9fafb] text-xs" style={{
                            animation: 'blink 1s infinite',
                            display: 'inline-block'
                          }}>
                            |
                          </div>
                        )}
                      </div>
                      {/* Model selector - bottom left */}
                      <div className="absolute left-3 bottom-3 flex items-center gap-1.5">
                        <Package className="w-3.5 h-3.5 text-[#71717a]" />
                        <span className="text-[10px] text-[#71717a] font-medium">VMM</span>
                        <ChevronDown className="w-3 h-3 text-[#71717a]" />
                      </div>
                      
                      {/* Action buttons - bottom right */}
                      <div className="absolute right-3 bottom-3 flex gap-1.5">
                        <div className="h-6 w-6 flex items-center justify-center">
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
                          Assess coordination risk
                        </button>
                        <button className="rounded-full px-3 py-1 text-[10px] border border-[#2a2a2a] bg-[#1a1a1a] hover:bg-[#2a2a2a] text-[#a1a1aa] hover:text-[#f9fafb] flex items-center gap-1.5">
                          <TrendingUp className="w-2.5 h-2.5" />
                          Prove competitive behavior
                        </button>
                        <button className="rounded-full px-3 py-1 text-[10px] border border-[#2a2a2a] bg-[#1a1a1a] hover:bg-[#2a2a2a] text-[#a1a1aa] hover:text-[#f9fafb] flex items-center gap-1.5">
                          <Database className="w-2.5 h-2.5" />
                          Export evidence bundle
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>              </div>
            )}

            {activeTab === "dashboard" && (
              /* Dashboard View */
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
                                      {selectedTimeframe === "30d" ? "Aug 06 - Sep 10" : 
                                       selectedTimeframe === "6m" ? "Mar '25 - Sep '25" : 
                                       selectedTimeframe === "1y" ? "Sep '24 - Sep '25" :
                                       "Jan 01 - Sep 05"}
                                    </button>
                                    <div className="flex gap-1">
                                      <button 
                                        onClick={() => setSelectedTimeframe("30d")}
                                        className={`text-xs px-2 py-1 ${
                                          selectedTimeframe === "30d" 
                                            ? "text-[#f9fafb] bg-[#3a3a3a] rounded" 
                                            : "text-[#a1a1aa] hover:text-[#f9fafb]"
                                        }`}
                                      >
                                        30d
                                      </button>
                                      <button 
                                        onClick={() => setSelectedTimeframe("6m")}
                                        className={`text-xs px-2 py-1 ${
                                          selectedTimeframe === "6m" 
                                            ? "text-[#f9fafb] bg-[#3a3a3a] rounded" 
                                            : "text-[#a1a1aa] hover:text-[#f9fafb]"
                                        }`}
                                      >
                                        6m
                                      </button>
                                      <button 
                                        onClick={() => setSelectedTimeframe("1y")}
                                        className={`text-xs px-2 py-1 ${
                                          selectedTimeframe === "1y" 
                                            ? "text-[#f9fafb] bg-[#3a3a3a] rounded" 
                                            : "text-[#a1a1aa] hover:text-[#f9fafb]"
                                        }`}
                                      >
                                        1y
                                      </button>
                                      <button 
                                        onClick={() => setSelectedTimeframe("YTD")}
                                        className={`text-xs px-2 py-1 ${
                                          selectedTimeframe === "YTD" 
                                            ? "text-[#f9fafb] bg-[#3a3a3a] rounded" 
                                            : "text-[#a1a1aa] hover:text-[#f9fafb]"
                                        }`}
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
                          <div className="text-xs text-[#a1a1aa]">Total Market Share</div>
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
                                    "FNB": 21,
                                    "ABSA": 21,
                                    "Standard Bank": 26,
                                    "Nedbank": 16
                                  };
                                  
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
                                            {entry.name}: <span className="font-bold">{entry.value} bps</span> | <span className="text-[#a1a1aa]">{marketShare[entry.name as keyof typeof marketShare]}% share</span>
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  );
                                }
                                return null;
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
                            <div className="text-[10px] text-[#a1a1aa]">How steady your prices are compared to competitors</div>
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
                    <div className="border-t border-[#2a2a2a]/70 border-opacity-70" style={{borderTopWidth: '0.5px'}}></div>
                    
                    {/* Price Synchronization */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <GitBranch className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Price Synchronization</div>
                            <div className="text-[10px] text-[#a1a1aa]">How much your prices move together with other banks</div>
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
                    <div className="border-t border-[#2a2a2a]/70 border-opacity-70" style={{borderTopWidth: '0.5px'}}></div>
                    
                    {/* Environmental Sensitivity */}
                    <div className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                          <Activity className="w-4 h-4 text-[#a1a1aa]" />
                        <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Environmental Sensitivity</div>
                            <div className="text-[10px] text-[#a1a1aa]">How well you respond to market changes and economic events</div>
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
                    <div className="border-t border-[#2a2a2a]/70 border-opacity-70" style={{borderTopWidth: '0.5px'}}></div>
                    
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

            {activeTab === "events" && (
              /* Events Log View */
              <div className="max-w-6xl mx-auto">
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-4">
                    {/* Header with title and controls */}
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-2 text-xs text-[#a1a1aa]">
                        <h1 className="text-lg font-medium text-[#f9fafb] mr-4">All Events</h1>
                        <button 
                          onClick={() => setIsCalendarOpen(!isCalendarOpen)}
                          className="rounded-full px-3 py-1 text-xs border border-[#3a3a3a] bg-transparent hover:bg-[#2a2a2a]/50 text-[#a1a1aa] hover:text-[#f9fafb] flex items-center gap-1"
                        >
                          <CalendarIcon className="h-3 w-3" />
                          Aug 28 - Sep 05
                        </button>
                        <div className="flex gap-1">
                          <button 
                            onClick={() => setSelectedTimeframe("30d")}
                            className={`text-xs px-2 py-1 ${
                              selectedTimeframe === "30d" 
                                ? "text-[#f9fafb] bg-[#3a3a3a] rounded" 
                                : "text-[#a1a1aa] hover:text-[#f9fafb]"
                            }`}
                          >
                            1d
                          </button>
                          <button 
                            onClick={() => setSelectedTimeframe("6m")}
                            className={`text-xs px-2 py-1 ${
                              selectedTimeframe === "6m" 
                                ? "text-[#f9fafb] bg-[#3a3a3a] rounded" 
                                : "text-[#a1a1aa] hover:text-[#f9fafb]"
                            }`}
                          >
                            7d
                          </button>
                          <button 
                            onClick={() => setSelectedTimeframe("1y")}
                            className={`text-xs px-2 py-1 ${
                              selectedTimeframe === "1y" 
                                ? "text-[#f9fafb] bg-[#3a3a3a] rounded" 
                                : "text-[#a1a1aa] hover:text-[#f9fafb]"
                            }`}
                          >
                            30d
                          </button>
                        </div>
                      </div>
                      <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-[#1a1a1a] text-[#a1a1aa] hover:text-[#f9fafb] flex items-center gap-1.5">
                        <Database className="w-3 h-3" />
                        Export CSV
                      </button>
                    </div>

                    {/* Events Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-[#2a2a2a]">
                            <th className="text-left py-3 px-2 text-[#a1a1aa] font-medium">Date</th>
                            <th className="text-left py-3 px-2 text-[#a1a1aa] font-medium">Event Type</th>
                            <th className="text-left py-3 px-2 text-[#a1a1aa] font-medium">Severity</th>
                            <th className="text-left py-3 px-2 text-[#a1a1aa] font-medium">Details</th>
                            <th className="text-left py-3 px-2 text-[#a1a1aa] font-medium">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-b border-[#2a2a2a]/50">
                            <td className="py-3 px-2 text-[#f9fafb]">Sep 5, 04:46 PM</td>
                            <td className="py-3 px-2 text-[#f9fafb]">Price Coordination</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#fca5a5]/20 text-[#fca5a5]">High Risk</span>
                            </td>
                            <td className="py-3 px-2 text-[#a1a1aa]">Synchronized price movements detected across 3 banks</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#a7f3d0]/20 text-[#a7f3d0]">Active</span>
                            </td>
                          </tr>
                          <tr className="border-b border-[#2a2a2a]/50">
                            <td className="py-3 px-2 text-[#f9fafb]">Sep 5, 03:49 PM</td>
                            <td className="py-3 px-2 text-[#f9fafb]">Market Anomaly</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#fde68a]/20 text-[#fde68a]">Medium Risk</span>
                            </td>
                            <td className="py-3 px-2 text-[#a1a1aa]">Unusual trading pattern in ABSA securities</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#a7f3d0]/20 text-[#a7f3d0]">Resolved</span>
                            </td>
                          </tr>
                          <tr className="border-b border-[#2a2a2a]/50">
                            <td className="py-3 px-2 text-[#f9fafb]">Sep 5, 02:15 PM</td>
                            <td className="py-3 px-2 text-[#f9fafb]">Compliance Check</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#a7f3d0]/20 text-[#a7f3d0]">Low Risk</span>
                            </td>
                            <td className="py-3 px-2 text-[#a1a1aa]">Routine VMM analysis completed successfully</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#a7f3d0]/20 text-[#a7f3d0]">Completed</span>
                            </td>
                          </tr>
                          <tr className="border-b border-[#2a2a2a]/50">
                            <td className="py-3 px-2 text-[#f9fafb]">Sep 5, 01:30 PM</td>
                            <td className="py-3 px-2 text-[#f9fafb]">Data Quality</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#fde68a]/20 text-[#fde68a]">Medium Risk</span>
                            </td>
                            <td className="py-3 px-2 text-[#a1a1aa]">Missing data points in Standard Bank feed</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#fca5a5]/20 text-[#fca5a5]">Investigated</span>
                            </td>
                          </tr>
                          <tr className="border-b border-[#2a2a2a]/50">
                            <td className="py-3 px-2 text-[#f9fafb]">Sep 5, 12:45 PM</td>
                            <td className="py-3 px-2 text-[#f9fafb]">Price Coordination</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#a7f3d0]/20 text-[#a7f3d0]">Low Risk</span>
                            </td>
                            <td className="py-3 px-2 text-[#a1a1aa]">Normal competitive pricing behavior observed</td>
                            <td className="py-3 px-2">
                              <span className="px-2 py-1 rounded text-[10px] bg-[#a7f3d0]/20 text-[#a7f3d0]">Completed</span>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  )
}
