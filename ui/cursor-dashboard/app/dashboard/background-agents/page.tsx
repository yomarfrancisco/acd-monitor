"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SquareChevronRight, Brain, ScaleIcon, Target, Shield } from "lucide-react";

// Dashboard CTA button styling - pastel blue bg + black text for the 13 specific CTA buttons
const dashboardCtaBtnClass = "bg-[#AFC8FF] text-black hover:bg-[#9FBCFF] active:bg-[#95B4FF] ring-1 ring-inset ring-[#8FB3FF]/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6FA0FF] shadow-sm text-[9px] h-5 px-2 font-normal rounded-full disabled:bg-[#AFC8FF]/60 disabled:text-black/60 disabled:ring-[#8FB3FF]/50 disabled:cursor-not-allowed disabled:opacity-100";

export default function Page() {
  const [evidenceLoading, setEvidenceLoading] = useState(false);

  const handleEvidenceExport = () => {
    setEvidenceLoading(true);
    // Simulate loading
    setTimeout(() => setEvidenceLoading(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Quick Analysis */}
      <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
        <CardContent className="p-4">
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
            <h2 className="text-sm font-medium text-[#f9fafb]">Available Agents</h2>
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
              <Button
                size="sm"
                className={dashboardCtaBtnClass}
              >
                Deploy
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
                  <ScaleIcon className="w-4 h-4 text-[#a1a1aa] self-center" />
                  <div>
                    <div className="text-xs font-medium text-[#f9fafb]">Compliance Monitor</div>
                    <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                      Accuracy: 98.7% • Response time: 0.8s
                    </div>
                  </div>
                </div>
              </div>
              <Button
                size="sm"
                className={dashboardCtaBtnClass}
              >
                Deploy
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
                  <Target className="w-4 h-4 text-[#a1a1aa] self-center" />
                  <div>
                    <div className="text-xs font-medium text-[#f9fafb]">Risk Assessment</div>
                    <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                      Accuracy: 96.1% • Response time: 1.5s
                    </div>
                  </div>
                </div>
              </div>
              <Button
                size="sm"
                className={dashboardCtaBtnClass}
              >
                Deploy
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
                  <Shield className="w-4 h-4 text-[#a1a1aa] self-center" />
                  <div>
                    <div className="text-xs font-medium text-[#f9fafb]">Security Audit</div>
                    <div className="text-[10px] text-[#a1a1aa] mt-0.5">
                      Accuracy: 99.2% • Response time: 2.1s
                    </div>
                  </div>
                </div>
              </div>
              <Button
                size="sm"
                className={dashboardCtaBtnClass}
              >
                Deploy
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}