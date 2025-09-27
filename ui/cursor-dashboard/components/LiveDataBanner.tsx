import React from 'react';
import { env } from '@/lib/env';

interface LiveDataBannerProps {
  className?: string;
}

export function LiveDataBanner({ className = '' }: LiveDataBannerProps) {
  if (!env.isPreview) {
    return null;
  }

  const isLive = env.isLive && !env.useDemo;
  const isDemo = env.useDemo;

  return (
    <div className={`fixed bottom-4 right-4 z-50 ${className}`}>
      {isLive ? (
        <div className="bg-green-600 text-white px-3 py-2 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2">
          <div className="w-2 h-2 bg-green-300 rounded-full animate-pulse"></div>
          Preview – Live Feed Active
        </div>
      ) : isDemo ? (
        <div className="bg-red-600 text-white px-3 py-2 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2">
          <div className="w-2 h-2 bg-red-300 rounded-full"></div>
          Preview – DEMO MODE
        </div>
      ) : (
        <div className="bg-yellow-600 text-white px-3 py-2 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2">
          <div className="w-2 h-2 bg-yellow-300 rounded-full"></div>
          Preview – Unknown Mode
        </div>
      )}
    </div>
  );
}

export default LiveDataBanner;
