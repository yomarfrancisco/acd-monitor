import React from 'react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid, ReferenceLine, Area, ComposedChart } from 'recharts';
import { useTimeseriesData } from '@/lib/useTimeseriesData';

interface TimeseriesChartProps {
  timeframe: string;
  region?: string;
  industry?: string;
  height?: number;
}

export function TimeseriesChart({ 
  timeframe, 
  region = 'US', 
  industry = 'CRYPTO',
  height = 320 
}: TimeseriesChartProps) {
  const { data, loading, error } = useTimeseriesData(timeframe, region, industry);

  if (loading) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="animate-pulse">
          <div className="h-4 bg-[#2a2a2a] rounded w-32 mb-2"></div>
          <div className="h-4 bg-[#2a2a2a] rounded w-24"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="text-center">
          <div className="text-sm text-[#fca5a5] mb-2">Chart Error</div>
          <div className="text-xs text-[#71717a]">{error}</div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-80 flex items-center justify-center">
        <div className="text-center">
          <div className="text-sm text-[#a1a1aa] mb-2">No Data</div>
          <div className="text-xs text-[#71717a]">No timeseries data available</div>
        </div>
      </div>
    );
  }

  // Transform data for Recharts
  const chartData = data.series.map(item => ({
    date: new Date(item.t).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    }),
    value: item.v,
    timestamp: item.t
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-3 shadow-lg">
          <p className="text-[#a1a1aa] text-xs mb-1">{label}</p>
          <p className="text-[#f9fafb] text-sm font-medium">
            CI: {payload[0].value.toFixed(2)}
          </p>
          <div className="text-[#71717a] text-xs mt-1">
            <div>Amber: {data.thresholds.amber}</div>
            <div>Red: {data.thresholds.red}</div>
            <div>Critical: {data.thresholds.critical}</div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="h-80 relative focus:outline-none" style={{ outline: "none" }}>
      <ResponsiveContainer width="100%" height="100%" style={{ outline: "none" }}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
          
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
            domain={[0, 10]}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          {/* Threshold bands */}
          <Area
            type="monotone"
            dataKey={() => data.thresholds.critical}
            fill="#fca5a5"
            fillOpacity={0.1}
            stroke="none"
          />
          <Area
            type="monotone"
            dataKey={() => data.thresholds.red}
            fill="#fbbf24"
            fillOpacity={0.1}
            stroke="none"
          />
          <Area
            type="monotone"
            dataKey={() => data.thresholds.amber}
            fill="#fde047"
            fillOpacity={0.1}
            stroke="none"
          />
          
          {/* Baseline reference line */}
          {data.baseline && (
            <ReferenceLine
              y={data.baseline}
              stroke="#71717a"
              strokeDasharray="2 2"
              strokeWidth={1}
            />
          )}
          
          {/* Main data line */}
          <Line
            type="monotone"
            dataKey="value"
            stroke="#52525b"
            strokeWidth={2}
            dot={{ fill: "#52525b", strokeWidth: 1.5, r: 3 }}
            activeDot={{ r: 4, fill: "#52525b", strokeWidth: 2, stroke: "#0f0f10" }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
