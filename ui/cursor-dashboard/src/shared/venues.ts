export type VenueKey = 'binance' | 'okx' | 'bybit' | 'kraken' | 'coinbase';

export const VENUES: VenueKey[] = [
  'binance',
  'okx',
  'bybit',
  'kraken',
  'coinbase',
];

export const VENUE_LABEL: Record<VenueKey, string> = {
  binance: 'Binance',
  okx: 'OKX',
  bybit: 'Bybit',
  kraken: 'Kraken',
  coinbase: 'Coinbase',
};

export const VENUE_COLOR: Record<VenueKey, string> = {
  binance: '#4B82FF',
  okx: '#999999',
  bybit: '#8CA8FF',
  kraken: '#B4B4FF',
  coinbase: '#FFA638', // keep existing Coinbase accent
};
