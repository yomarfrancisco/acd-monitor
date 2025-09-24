export type UiVenue = 'binance' | 'coinbase' | 'bybit' | 'kraken';
export type DataKey = 'fnb' | 'absa' | 'nedbank' | 'standard';

export const venueToUi: Record<string, UiVenue> = {
  binance: 'binance',
  okx: 'coinbase',   // UI uses Coinbase icon for OKX
  bybit: 'bybit',
  kraken: 'kraken',
};

export const uiKeyToDataKey: Record<UiVenue, DataKey> = {
  binance: 'fnb',
  coinbase: 'absa',  // OKX→Coinbase placeholder in existing UI
  bybit: 'nedbank',
  kraken: 'standard',
};

// Helper function to get available UI venues from successful exchanges
export function getAvailableUiVenues(successfulExchanges: any[]): UiVenue[] {
  return Array.from(
    new Set(successfulExchanges
      .map(r => venueToUi[r.venue])
      .filter(Boolean))
  );
}
