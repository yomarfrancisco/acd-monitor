"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts"
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

export default function CursorDashboard() {
  const [activeTab, setActiveTab] = useState<"agents" | "dashboard">("agents")
  const [selectedTimeframe, setSelectedTimeframe] = useState<"30d" | "6m" | "1y" | "YTD">("YTD")
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)
  const [selectedDate, setSelectedDate] = useState<{from: Date | undefined, to?: Date | undefined} | undefined>({
    from: new Date(),
    to: new Date()
  })
  const [isClient, setIsClient] = useState(false)

  useEffect(() => {
    setIsClient(true)
  }, [])

  // Close calendar when switching to agents tab
  const handleTabChange = (tab: "agents" | "dashboard") => {
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
                  <p className="text-[10px] text-[#a1a1aa] mb-2.5">ygor.francisco@gmail.com</p>

                  <div className="bg-[#1a1a1a] rounded-md p-1.5 mb-2.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-[#f9fafb]">
                      <User className="w-3.5 h-3.5" />
                      Overview
                    </div>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="text-[#a1a1aa] px-1.5 py-0.5">Configuration</div>
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
                    Evidence Logs
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
            {activeTab === "agents" ? (
              /* Agents View */
              <div className="max-w-xl mx-auto">
                <div className="flex flex-col items-center justify-center min-h-[45vh] space-y-5">
                  <div className="w-full space-y-3">
                    <div className="relative">
                      <textarea
                        placeholder="Ask RBB to assess the competitive effects"
                        className="w-full h-20 bg-[#1a1a1a] rounded-lg text-[#f9fafb] placeholder-[#a1a1aa] pr-12 px-4 py-4 text-xs resize-none focus:outline-none focus:ring-2 focus:ring-[#60a5fa] shadow-[0_1px_0_rgba(0,0,0,0.20)]"
                        rows={3}
                      />
                      <Button
                        size="sm"
                        className="absolute right-3 top-3 h-7 w-7 p-0 bg-[#3f3f46]/80 hover:bg-[#3f3f46]/90 border-0"
                      >
                        <Search className="w-3.5 h-3.5 text-[#27272a]" />
                      </Button>
                    </div>

                    <div className="space-y-2.5">
                      <p className="text-[10px] text-[#a1a1aa] text-center">Try these examples to get started</p>

                      <div className="flex flex-wrap gap-1.5 justify-center">
                        <button className="text-[#a1a1aa] hover:text-[#f9fafb] hover:underline text-[10px] px-2 py-1 flex items-center gap-1.5">
                          <Zap className="w-2.5 h-2.5" />
                          Assess collusion risk
                        </button>
                        <button className="text-[#a1a1aa] hover:text-[#f9fafb] hover:underline text-[10px] px-2 py-1 flex items-center gap-1.5">
                          <FileText className="w-2.5 h-2.5" />
                          Generate compliance report
                        </button>
                        <button className="text-[#a1a1aa] hover:text-[#f9fafb] hover:underline text-[10px] px-2 py-1 flex items-center gap-1.5">
                          <CalendarIcon className="w-2.5 h-2.5" />
                          Book a meeting with RBB
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* Dashboard View */
              <div className="space-y-3 max-w-2xl">
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Enterprise Plan</h2>
                        <p className="text-xs text-[#a1a1aa] mb-3 max-w-[280px] leading-relaxed">
                          Real-time Diagnostic with regulatory compliance and VMM engine engaged.
                        </p>
                        <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-[#1a1a1a] text-[#a1a1aa] hover:text-[#f9fafb]">
                          Manage Subscription
                        </button>
                      </div>
                      <div className="rounded-lg bg-[#1e1e1e] shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex-shrink-0">
                        <div className="text-right">
                          <div className="text-xs font-bold text-[#f9fafb] mb-1">$0 / $6k</div>
                          <p className="text-xs text-[#a1a1aa] mb-2">Usage-Based Spending this Month</p>
                          <button className="rounded-full px-3 py-1 text-xs border border-[#2a2a2a] bg-transparent hover:bg-[#1a1a1a] text-[#a1a1aa] hover:text-[#f9fafb]">
                            Edit Limit
                          </button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2 text-xs text-[#a1a1aa]">
                        {isClient && activeTab === "dashboard" && (
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
                        )}
                      </div>
                      {isClient && activeTab === "dashboard" && (
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
                      )}
                    </div>

                    <div className="mb-4">
                      <h3 className="text-xs font-medium text-[#f9fafb] mb-3">Your Coordination Risk</h3>
                      <div className="grid grid-cols-2 gap-6 mb-6">
                        <div className="rounded-lg bg-[#1e1e1e] shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                          <div className="text-xl font-bold text-[#f9fafb]">14 out of 100</div>
                          <div className="text-xs text-[#a1a1aa]">Low Risk</div>
                        </div>
                        <div>
                          <div className="text-xl font-bold text-[#f9fafb]">86%</div>
                          <div className="text-xs text-[#a1a1aa]">Total Market Share</div>
                        </div>
                      </div>

                      <div className="h-56">
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
                                value: "CDS Spread %",
                                angle: -90,
                                position: "insideLeft",
                                style: { textAnchor: "middle", fill: "#a1a1aa", fontSize: 10 },
                              }}
                            />
                            <Tooltip
                              content={({ active, payload, label }) => {
                                if (active && payload && payload.length) {
                                  return (
                                    <div className="bg-[#2a2a2a] border border-[#3a3a3a] rounded-lg p-2 shadow-lg">
                                      <p className="text-[#a1a1aa] text-xs mb-1">{label}</p>
                                      {payload.map((entry, index) => (
                                        <div key={index} className="flex items-center gap-2 text-xs">
                                          <div 
                                            className="w-2 h-2 rounded-full" 
                                            style={{ backgroundColor: entry.color }}
                                          />
                                          <span className="text-[#f9fafb]">{entry.name}: {entry.value}</span>
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
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-[#f9fafb] font-bold text-sm">25</div>
                          <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Separator line */}
                    <div className="border-t border-[#2a2a2a]"></div>
                    
                    {/* Price Synchronization */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <GitBranch className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Price Synchronization</div>
                            <div className="text-[10px] text-[#a1a1aa]">How much your prices move together with other banks</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-[#f9fafb] font-bold text-sm">18</div>
                          <div className="text-[10px] text-[#a1a1aa]">out of 100</div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Separator line */}
                    <div className="border-t border-[#2a2a2a]"></div>
                    
                    {/* Environmental Sensitivity */}
                    <div className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <Activity className="w-4 h-4 text-[#a1a1aa]" />
                          <div>
                            <div className="text-[#f9fafb] font-medium text-xs">Environmental Sensitivity</div>
                            <div className="text-[10px] text-[#a1a1aa]">How well you respond to market changes and economic events</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-[#f9fafb] font-bold text-sm">82</div>
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
                    <div className="border-t border-[#2a2a2a]"></div>
                    
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
          </main>
        </div>
      </div>
    </div>
  )
}
