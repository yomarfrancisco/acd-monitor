import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CalendarCheck2, ChevronDown, SquarePen } from 'lucide-react';
import { fetchTyped } from '@/lib/backendAdapter';
import { EventsResponseSchema } from '@/types/api.schemas';
import type { EventsResponse } from '@/types/api';

interface EventsTableProps {
  timeframe: string;
  region?: string;
  industry?: string;
  onLogEvent?: () => void;
}

export function EventsTable({ 
  timeframe, 
  region = 'US', 
  industry = 'CRYPTO',
  onLogEvent 
}: EventsTableProps) {
  const [events, setEvents] = useState<EventsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const fetchEvents = async (cursor?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        timeframe,
        region,
        industry,
        limit: '50',
      });
      
      if (cursor) {
        params.append('cursor', cursor);
      }
      
      const result = await fetchTyped(`/events?${params}`, EventsResponseSchema);
      setEvents(result as EventsResponse);
      
      // Note: The API doesn't currently return nextCursor, but we'll handle it when it does
      setNextCursor(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch events');
      console.error('Events fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [timeframe, region, industry]);

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'low':
        return 'text-[#a7f3d0]';
      case 'medium':
        return 'text-[#fde047]';
      case 'high':
        return 'text-[#fca5a5]';
      default:
        return 'text-[#a1a1aa]';
    }
  };

  const getSeverityBg = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'low':
        return 'bg-[#a7f3d0]/10';
      case 'medium':
        return 'bg-[#fde047]/10';
      case 'high':
        return 'bg-[#fca5a5]/10';
      default:
        return 'bg-[#2a2a2a]';
    }
  };

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date();
    const eventTime = new Date(timestamp);
    const diffMs = now.getTime() - eventTime.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      return `${diffDays}d ago`;
    }
  };

  if (loading && !events) {
    return (
      <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
        <CardContent className="p-0">
          <div className="px-4 py-3 border-b border-[#2a2a2a]">
            <h2 className="text-sm font-medium text-[#f9fafb]">All Events</h2>
          </div>
          <div className="p-3">
            <div className="animate-pulse space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-4 h-4 bg-[#2a2a2a] rounded"></div>
                    <div>
                      <div className="h-3 bg-[#2a2a2a] rounded w-32 mb-1"></div>
                      <div className="h-2 bg-[#2a2a2a] rounded w-48 mb-1"></div>
                      <div className="h-2 bg-[#2a2a2a] rounded w-16"></div>
                    </div>
                  </div>
                  <div className="h-6 bg-[#2a2a2a] rounded w-12"></div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
        <CardContent className="p-0">
          <div className="px-4 py-3 border-b border-[#2a2a2a]">
            <h2 className="text-sm font-medium text-[#f9fafb]">All Events</h2>
          </div>
          <div className="p-3">
            <div className="text-center">
              <div className="text-sm text-[#fca5a5] mb-2">Events Error</div>
              <div className="text-xs text-[#71717a]">{error}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
      <CardContent className="p-0">
        {/* Title Section */}
        <div className="px-4 py-3 border-b border-[#2a2a2a]">
          <h2 className="text-sm font-medium text-[#f9fafb]">All Events</h2>
        </div>

        {/* Events List */}
        {events?.items && events.items.length > 0 ? (
          <div className="divide-y divide-[#2a2a2a]">
            {events.items.map((event, index) => (
              <div key={event.id || index} className="p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <CalendarCheck2 className="w-4 h-4 text-[#a1a1aa]" />
                    <div>
                      <div className="text-[#f9fafb] font-medium text-xs">{event.title}</div>
                      <div className="text-[10px] text-[#a1a1aa]">
                        {event.description}
                      </div>
                      <div className="text-[9px] text-[#a1a1aa] mt-0.5">
                        {formatTimeAgo(event.ts)} • {event.durationMin ? `${event.durationMin}m` : 'ongoing'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1.5">
                      <div className="text-[#f9fafb] font-bold text-sm">{event.riskScore}</div>
                      <div className={`px-2 py-1 rounded-full text-[10px] font-medium ${getSeverityBg(event.severity)} ${getSeverityColor(event.severity)}`}>
                        {event.severity}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-3">
            <div className="text-center">
              <div className="text-sm text-[#a1a1aa] mb-2">No Events</div>
              <div className="text-xs text-[#71717a]">No events found for the selected timeframe</div>
            </div>
          </div>
        )}

        {/* Load More Button (if nextCursor exists) */}
        {nextCursor && (
          <div className="px-4 py-3 border-t border-[#2a2a2a]">
            <Button
              variant="outline"
              size="sm"
              className="w-full text-xs bg-transparent border-[#2a2a2a] text-[#f9fafb] hover:bg-bg-tile"
              onClick={() => fetchEvents(nextCursor)}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Load More'}
            </Button>
          </div>
        )}

        {/* Pagination Info */}
        {events?.items && events.items.length > 0 && (
          <div className="px-4 py-3 border-t border-[#2a2a2a]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 text-[10px] text-[#a1a1aa]">
                <span>Showing 1 - {events.items.length} of {events.items.length} events</span>
                <div className="flex items-center gap-2">
                  <span>Rows per page:</span>
                  <select className="bg-transparent border border-[#2a2a2a] rounded px-2 py-1 text-[#f9fafb] text-[10px]">
                    <option value="50">50</option>
                    <option value="100">100</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
