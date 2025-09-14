"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { CalendarIcon, Clock } from "lucide-react";

// PageWrapper removed - was causing layout conflicts

// Different data sets for different time periods
const analyticsData30d = [
  { date: "Aug 6", fnb: 100, absa: 95, standard: 105, nedbank: 98 },
  { date: "Aug 13", fnb: 150, absa: 145, standard: 155, nedbank: 148 },
  { date: "Aug 20", fnb: 200, absa: 190, standard: 210, nedbank: 195 },
  { date: "Aug 27", fnb: 250, absa: 240, standard: 260, nedbank: 245 },
  { date: "Sep 3", fnb: 300, absa: 290, standard: 310, nedbank: 295 },
  { date: "Sep 10", fnb: 350, absa: 330, standard: 370, nedbank: 340 },
];

const analyticsData6m = [
  { date: "Mar '25", fnb: 80, absa: 75, standard: 85, nedbank: 78 },
  { date: "Apr '25", fnb: 120, absa: 115, standard: 125, nedbank: 118 },
  { date: "May '25", fnb: 180, absa: 175, standard: 185, nedbank: 178 },
  { date: "Jun '25", fnb: 220, absa: 210, standard: 230, nedbank: 215 },
  { date: "Jul '25", fnb: 280, absa: 270, standard: 290, nedbank: 275 },
  { date: "Aug '25", fnb: 320, absa: 310, standard: 330, nedbank: 315 },
  { date: "Sep '25", fnb: 350, absa: 330, standard: 370, nedbank: 340 },
];

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
];

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
];

export default function Page() {
  const [selectedTimeframe, setSelectedTimeframe] = useState<"30d" | "6m" | "1y" | "ytd">("ytd");
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  const currentData = selectedTimeframe === "30d" ? analyticsData30d :
                     selectedTimeframe === "6m" ? analyticsData6m :
                     selectedTimeframe === "1y" ? analyticsData1y : analyticsDataYTD;

  return (
    <div className="space-y-6">
      {/* Cards: 2x2 on desktop, single column on mobile */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
            <CardContent className="p-4">
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
              {isClient && (
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
            <h3 className="text-xs font-medium text-[#f9fafb] mb-3">Algorithmic Cartel Diagnostic</h3>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mb-10">
              <div className="rounded-lg bg-bg-surface shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 relative">
                <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-bg-tile border border-[#2a2a2a] rounded-full px-2 py-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-[10px] text-[#a1a1aa]">LIVE</span>
                </div>
                <div className="text-xl font-bold text-[#f9fafb]">14 out of 100</div>
                <div className="text-xs text-[#a7f3d0]">Low Risk</div>
              </div>
              <div className="rounded-lg bg-bg-surface/40 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xl font-bold text-[#f9fafb]">
                      {selectedTimeframe === "30d" ? "78" : 
                       selectedTimeframe === "6m" ? "82" : 
                       selectedTimeframe === "1y" ? "79" : "84"}%
                    </div>
                    <div className="text-xs text-[#a1a1aa]">
                      {selectedTimeframe === "30d" ? "30d" : 
                       selectedTimeframe === "6m" ? "6m" : 
                       selectedTimeframe === "1y" ? "1y" : 
                       selectedTimeframe === "ytd" ? "YTD" : "Cal"} Price Leader
                    </div>
                  </div>
                  <div className="flex items-center -space-x-2">
                    <div className="w-8 h-8 rounded-full border-2 border-[#1a1a1a] overflow-hidden bg-white">
                      <img 
                        src="/fnb-logo.png" 
                        alt="FNB" 
                        className="w-full h-full object-contain p-0.5"
                      />
                    </div>
                    <div className="w-8 h-8 rounded-full border-2 border-[#1a1a1a] overflow-hidden bg-white opacity-80">
                      <img 
                        src="/absa-logo.png" 
                        alt="ABSA" 
                        className="w-full h-full object-contain p-0.5"
                      />
                    </div>
                    <div className="w-8 h-8 rounded-full border-2 border-[#1a1a1a] overflow-hidden bg-white opacity-60">
                      <img 
                        src="/nedbank-logo.png" 
                        alt="Nedbank" 
                        className="w-full h-full object-contain p-0.5"
                      />
                    </div>
                    <div className="w-8 h-8 rounded-full border-2 border-[#1a1a1a] overflow-hidden bg-white opacity-40">
                      <img 
                        src="/standard-logo.png" 
                        alt="Standard Bank" 
                        className="w-full h-full object-contain p-0.5"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="h-80 relative focus:outline-none bg-bg-surface rounded-lg flex items-center justify-center">
              <div className="text-center">
                <div className="text-sm text-[#a1a1aa] mb-2">Chart Placeholder</div>
                <div className="text-xs text-[#71717a]">Interactive chart will be rendered here</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
        </section>

      {/* Chart/Table: full-width below cards */}
      <section className="w-full mt-6">
        {/* Chart/Table content goes here */}
      </section>
    </div>
  );
}