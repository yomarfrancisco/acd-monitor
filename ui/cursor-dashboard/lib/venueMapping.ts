export type UiVenue = 'binance' | 'okx' | 'coinbase' | 'bybit' | 'kraken';
export type DataKey = 'fnb' | 'absa' | 'nedbank' | 'standard' | 'coinbase';

export const venueToUi: Record<string, UiVenue> = {
  binance: 'binance',
  okx: 'okx',        // OKX now uses its own UI key
  bybit: 'bybit',
  kraken: 'kraken',
  coinbase: 'coinbase',  // Coinbase as separate venue
};

export const uiKeyToDataKey: Record<UiVenue, DataKey> = {
  binance: 'fnb',
  okx: 'absa',       // OKX keeps existing bank dataKey
  bybit: 'nedbank',
  kraken: 'standard',
  coinbase: 'coinbase',  // Coinbase gets new dataKey
};

// Venue metadata for display
export const venueMetadata: Record<UiVenue, { label: string; icon: string; color: string }> = {
  binance: { label: 'Binance', icon: '/binance_circle.png', color: '#60a5fa' },
  okx: { label: 'OKX', icon: '/OKX_circle.png', color: '#a1a1aa' },
  coinbase: { label: 'Coinbase', icon: '/coinbase_circle.png', color: '#f59e0b' },
  bybit: { label: 'Bybit', icon: '/bybit_circle.png', color: '#52525b' },
  kraken: { label: 'Kraken', icon: '/kraken_circle.png', color: '#71717a' },
};

// Helper function to get available UI venues from successful exchanges
export function getAvailableUiVenues(successfulExchanges: any[]): UiVenue[] {
  const venues = Array.from(
    new Set(successfulExchanges
      .map(r => venueToUi[r.venue])
      .filter(Boolean))
  );
  
  // Filter out Coinbase if not enabled in Preview
  if (process.env.NEXT_PUBLIC_ENABLE_COINBASE !== 'true') {
    return venues.filter(v => v !== 'coinbase');
  }
  
  return venues;
}
