import React, { useState, useEffect } from 'react';

interface SelftestIndicatorProps {
  className?: string;
}

export function SelftestIndicator({ className = "" }: SelftestIndicatorProps) {
  const [status, setStatus] = useState<'checking' | 'healthy' | 'error'>('checking');
  const [lastCheck, setLastCheck] = useState<Date | null>(null);

  const checkStatus = async () => {
    try {
      const response = await fetch('/api/selftest');
      if (response.ok) {
        setStatus('healthy');
      } else {
        setStatus('error');
      }
      setLastCheck(new Date());
    } catch (error) {
      setStatus('error');
      setLastCheck(new Date());
    }
  };

  useEffect(() => {
    checkStatus();
    // Check every 30 seconds
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = () => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'checking':
      default:
        return 'bg-yellow-500';
    }
  };

  const getStatusTitle = () => {
    switch (status) {
      case 'healthy':
        return 'System Healthy';
      case 'error':
        return 'System Error';
      case 'checking':
      default:
        return 'Checking...';
    }
  };

  return (
    <div 
      className={`flex items-center gap-2 ${className}`}
      title={getStatusTitle()}
    >
      <div 
        className={`w-2 h-2 rounded-full ${getStatusColor()} ${
          status === 'checking' ? 'animate-pulse' : ''
        }`}
      />
      {lastCheck && (
        <span className="text-[10px] text-[#71717a]">
          {Math.floor((Date.now() - lastCheck.getTime()) / 1000)}s ago
        </span>
      )}
    </div>
  );
}
