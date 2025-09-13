"use client";

import { Card, CardContent } from "@/components/ui/card";

export default function Page() {
  return (
    <div className="space-y-3 max-w-2xl">
      <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
        <CardContent className="p-6">
          <h2 className="text-sm font-medium text-[#f9fafb] mb-2">Health Checks</h2>
          <p className="text-xs text-[#a1a1aa] leading-relaxed">
            Monitor system health and performance metrics.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}