"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, Zap, Database, Cloud } from "lucide-react";

// Dashboard CTA button styling - pastel blue bg + black text for the 13 specific CTA buttons
const dashboardCtaBtnClass = "bg-[#AFC8FF] text-black hover:bg-[#9FBCFF] active:bg-[#95B4FF] ring-1 ring-inset ring-[#8FB3FF]/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6FA0FF] shadow-sm text-[9px] h-5 px-2 font-normal rounded-full disabled:bg-[#AFC8FF]/60 disabled:text-black/60 disabled:ring-[#8FB3FF]/50 disabled:cursor-not-allowed disabled:opacity-100";

export default function Page() {
  return (
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
    </div>
  );
}