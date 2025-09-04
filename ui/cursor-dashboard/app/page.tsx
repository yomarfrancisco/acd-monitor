"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from "recharts"
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
  Calendar,
} from "lucide-react"

const analyticsData = [
  { date: "Aug 26", value: 100 },
  { date: "Aug 27", value: 150 },
  { date: "Aug 28", value: 200 },
  { date: "Aug 29", value: 180 },
  { date: "Aug 30", value: 250 },
  { date: "Aug 31", value: 300 },
  { date: "Sep 01", value: 280 },
  { date: "Sep 02", value: 400 },
  { date: "Sep 03", value: 350 },
]

export default function CursorDashboard() {
  const [activeTab, setActiveTab] = useState<"agents" | "dashboard">("agents")

  return (
    <div className="min-h-screen bg-[#0f0f10] text-[#f9fafb] font-sans p-4">
      {/* Header */}
      <header className="border-b border-[#1a1a1a] px-5 py-2.5 relative">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/rbb-economics-logo.png" alt="RBB Economics" className="h-32 w-auto" />
          </div>

          <nav className="flex gap-5 absolute left-1/2 transform -translate-x-1/2">
            <button
              onClick={() => setActiveTab("agents")}
              className={`px-2.5 py-1 text-xs font-medium ${
                activeTab === "agents"
                  ? "text-[#f9fafb] border-b-2 border-[#f9fafb]"
                  : "text-[#a1a1aa] hover:text-[#f9fafb]"
              }`}
            >
              Agents
            </button>
            <button
              onClick={() => setActiveTab("dashboard")}
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
                    <Settings className="w-3.5 h-3.5" />
                    Data Sources
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <Users className="w-3.5 h-3.5" />
                    Adaptive Engines
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <Zap className="w-3.5 h-3.5" />
                    Health Checks
                  </div>
                </nav>

                <Separator className="bg-[#1a1a1a]" />

                <nav className="space-y-0.5">
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <Link className="w-3.5 h-3.5" />
                    Evidence Logs
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#a1a1aa] px-1.5 py-0.5 hover:bg-[#1a1a1a] rounded-md">
                    <BarChart3 className="w-3.5 h-3.5" />
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
                          <Calendar className="w-2.5 h-2.5" />
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
                        <span>Aug 26 - Sep 04</span>
                      </div>
                      <div className="flex gap-1">
                        <button className="text-[#a1a1aa] hover:text-[#f9fafb] text-xs px-2 py-1">1d</button>
                        <button className="text-[#a1a1aa] hover:text-[#f9fafb] text-xs px-2 py-1">7d</button>
                        <button className="text-[#a1a1aa] hover:text-[#f9fafb] text-xs px-2 py-1">30d</button>
                      </div>
                    </div>

                    <div className="mb-4">
                      <h3 className="text-xs font-medium text-[#f9fafb] mb-3">Your Coordination Risk</h3>
                      <div className="grid grid-cols-2 gap-6 mb-4">
                        <div>
                          <div className="text-xl font-bold text-[#f9fafb]">14 out of 100 • Low Risk</div>
                          <div className="text-xs text-[#a1a1aa]">CDS Spread</div>
                        </div>
                        <div>
                          <div className="text-xl font-bold text-[#f9fafb]">0</div>
                          <div className="text-xs text-[#a1a1aa]">Tabs Received</div>
                        </div>
                      </div>

                      <div className="h-40">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={analyticsData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
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
                            <Line
                              type="monotone"
                              dataKey="value"
                              stroke="#60a5fa"
                              strokeWidth={2}
                              dot={{ fill: "#60a5fa", strokeWidth: 2, r: 3 }}
                              activeDot={{ r: 4, fill: "#60a5fa" }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                        {console.log("[v0] Chart data:", analyticsData)}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Third tile: Market Data Feed */}
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <Github className="w-4 h-4 text-[#a1a1aa]" />
                        <div>
                          <div className="text-[#f9fafb] font-medium text-xs">Market Data Feed</div>
                          <div className="text-[10px] text-[#a1a1aa]">
                            Connect GitHub for Background Agents, Bugbot and enhanced codebase context
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
                  </CardContent>
                </Card>

                {/* Fourth tile: Regulatory Notices */}
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <Slack className="w-4 h-4 text-[#a1a1aa]" />
                        <div>
                          <div className="text-[#f9fafb] font-medium text-xs">Regulatory Notices</div>
                          <div className="text-[10px] text-[#a1a1aa]">Work with Background Agents from Slack</div>
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
                  </CardContent>
                </Card>

                {/* Fifth tile: Institutional Disclosures */}
                <Card className="bg-[#1a1a1a] border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <Link className="w-4 h-4 text-[#a1a1aa]" />
                        <div>
                          <div className="text-[#f9fafb] font-medium text-xs">Institutional Disclosures</div>
                          <div className="text-[10px] text-[#a1a1aa]">
                            Connect a Linear workspace to delegate issues to Background Agents
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
