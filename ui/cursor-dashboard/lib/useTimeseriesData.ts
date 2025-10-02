import { useState, useEffect } from 'react';

export interface TimeseriesData {
  series: Array<{ t: string; v: number }>;
  baseline?: number;
  thresholds: {
    amber: number;
    red: number;
    critical: number;
  };
  context: {
    timeframe: string;
    region: string;
    industry: string;
  };
}

export function useTimeseriesData(
  timeframe: string,
  region: string = 'US',
  industry: string = 'CRYPTO'
) {
  const [data, setData] = useState<TimeseriesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const params = new URLSearchParams({
          metric: 'ci',
          timeframe,
          region,
          industry,
        });
        
        const response = await fetch(`/api/metrics/timeseries?${params}`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch timeseries data');
        console.error('Timeseries fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeframe, region, industry]);

  return { data, loading, error };
}
