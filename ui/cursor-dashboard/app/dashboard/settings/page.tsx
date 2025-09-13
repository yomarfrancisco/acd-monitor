"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Activity, TrendingUp, BarChart3, ChevronDown } from "lucide-react";

export default function Page() {
  const [autoDetectMarketChanges, setAutoDetectMarketChanges] = useState(true);
  const [changeThreshold, setChangeThreshold] = useState("10%");
  const [confidenceLevel, setConfidenceLevel] = useState("95%");

  return (
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
                      Enable automatic detection of significant market changes
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
                      Minimum change required to trigger analysis
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
                      Statistical confidence required for alerts
                    </div>
                  </div>
                </div>
              </div>
              <div className="ml-4 relative">
                <select
                  value={confidenceLevel}
                  onChange={(e) => setConfidenceLevel(e.target.value)}
                  className="bg-bg-tile border border-[#2a2a2a] rounded-md px-3 py-1.5 text-xs text-[#f9fafb] cursor-pointer hover:bg-[#2a2a2a] focus:border-[#60a5fa] focus:outline-none focus:ring-1 focus:ring-[#60a5fa] transition-colors duration-200 appearance-none pr-8"
                >
                  <option value="90%">90%</option>
                  <option value="95%">95%</option>
                  <option value="99%">99%</option>
                </select>
                <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-3 h-3 text-[#71717a] pointer-events-none" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}