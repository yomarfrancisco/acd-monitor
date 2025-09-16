"use client";

import { Card, CardContent } from "@/components/ui/card";

export default function Page() {
  return (
    <div className="space-y-3 max-w-2xl">
      <Card className="bg-bg-tile border-0 shadow-[0_1px_0_rgba(0,0,0,0.20)] rounded-xl">
        <CardContent className="p-4">
          <h2 className="text-sm font-medium text-[#f9fafb] mb-2">Contact Us</h2>
          <p className="text-xs text-[#a1a1aa] leading-relaxed">
            Get in touch with our support team for assistance.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}