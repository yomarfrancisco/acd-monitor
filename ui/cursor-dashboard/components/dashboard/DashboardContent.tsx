"use client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid, ReferenceLine, Label } from "recharts";
import { CalendarIcon, Copy, RefreshCw, ImageUp, Camera, FolderClosed, Github, AlertTriangle } from "lucide-react";
import { RiskSummarySchema, MetricsOverviewSchema, HealthRunSchema, EventsResponseSchema, DataSourcesSchema, EvidenceExportSchema } from "@/types/api.schemas";
import { fetchTyped } from "@/lib/backendAdapter";
import { safe } from "@/lib/safe";
import { resilientFetch } from "@/lib/resilient-api";
import type { RiskSummary, MetricsOverview, HealthRun, EventsResponse, DataSources, EvidenceExport } from "@/types/api";
import { dashboardCtaBtnClass } from "@/lib/ui";

interface DashboardContentProps {
  activeSidebarItem: string;
  selectedTimeframe: "30d" | "6m" | "1y" | "ytd";
  isClient: boolean;
  isCalendarOpen: boolean;
  setIsCalendarOpen: (open: boolean) => void;
  riskSummaryLoading: boolean;
  riskSummaryError: string | null;
  riskSummary: RiskSummary | null;
  metricsLoading: boolean;
  metricsError: string | null;
  metricsOverview: MetricsOverview | null;
  healthLoading: boolean;
  healthError: string | null;
  healthRun: HealthRun | null;
  eventsLoading: boolean;
  eventsError: string | null;
  eventsResponse: EventsResponse | null;
  dataSourcesLoading: boolean;
  dataSourcesError: string | null;
  dataSources: DataSources | null;
  evidenceLoading: boolean;
  evidenceExport: EvidenceExport | null;
  handleEvidenceExport: () => void;
}

export default function DashboardContent({
  activeSidebarItem,
  selectedTimeframe,
  isClient,
  isCalendarOpen,
  setIsCalendarOpen,
  riskSummaryLoading,
  riskSummaryError,
  riskSummary,
  metricsLoading,
  metricsError,
  metricsOverview,
  healthLoading,
  healthError,
  healthRun,
  eventsLoading,
  eventsError,
  eventsResponse,
  dataSourcesLoading,
  dataSourcesError,
  dataSources,
  evidenceLoading,
  evidenceExport,
  handleEvidenceExport,
}: DashboardContentProps) {
  // This will contain all the dashboard content that was previously in the main page
  // For now, let's start with a simple structure and we can move the content over
  
  if (activeSidebarItem === "overview") {
    return (
      <div className="space-y-3">
        <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
          <CardContent className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="rounded-lg bg-bg-tile shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                <div>
                  <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Enterprise Plan</h2>
                  <p className="text-xs text-[#a1a1aa] mb-3 leading-relaxed">
                    Live monitoring with compliance tracking
                  </p>
                </div>
                <Button
                  size="sm"
                  className="bg-[#AFC8FF] text-black hover:bg-[#9FBCFF] text-[9px] h-5 px-2 font-normal"
                >
                  Manage Subscription
                </Button>
              </div>
              <div className="rounded-lg bg-bg-tile shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3 flex flex-col justify-between">
                <div>
                  <h2 className="text-sm font-medium text-[#f9fafb] mb-1">Usage</h2>
                  <p className="text-xs text-[#a1a1aa] mb-3">$0 / $60</p>
                </div>
                <Button
                  size="sm"
                  className="bg-[#AFC8FF] text-black hover:bg-[#9FBCFF] text-[9px] h-5 px-2 font-normal"
                >
                  Edit Limit
                </Button>
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
                            : "Jan '25 - Sep '25"}
                    </button>
                  </>
                )}
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="rounded-lg bg-bg-surface/40 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                <div className="text-xl font-bold text-[#f9fafb]">0</div>
                <div className="text-xs text-[#a1a1aa]">Lines of Agent Edits</div>
              </div>
              <div className="rounded-lg bg-bg-surface/40 shadow-[0_1px_0_rgba(0,0,0,0.10)] p-3">
                <div className="text-xl font-bold text-[#f9fafb]">0</div>
                <div className="text-xs text-[#a1a1aa]">Tabs Accepted</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Add other dashboard sections here as needed
  return (
    <div className="space-y-3">
      <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
        <CardContent className="p-4">
          <h2 className="text-sm font-medium text-[#f9fafb] mb-2">
            {activeSidebarItem === "configuration" && "Configuration"}
            {activeSidebarItem === "data-sources" && "Data Sources"}
            {activeSidebarItem === "ai-economists" && "AI Agents"}
            {activeSidebarItem === "health-checks" && "Health Checks"}
            {activeSidebarItem === "events-log" && "Events Log"}
            {activeSidebarItem === "billing" && "Billing & Invoices"}
            {activeSidebarItem === "compliance" && "Compliance Reports"}
            {activeSidebarItem === "contact" && "Contact Us"}
          </h2>
          <p className="text-xs text-[#a1a1aa]">
            Content for {activeSidebarItem} will be implemented here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
