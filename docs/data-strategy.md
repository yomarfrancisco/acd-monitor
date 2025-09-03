# Data Strategy & Independence

## Sources
- **Primary:** Client CDS desk quotes
- **Fallback:** S&P Global, ICE Data, Refinitiv, JSE bond spreads
- **Derived:** Bond-CDS basis, FX volatility, cross-currency swaps

## Validation
- Cross-compare sources
- Flag discrepancies > ±5bps
- Confidence score 0–100 (reliability, recency, variance)

## Fallback Triggers
- Auto: if client feed silent > X minutes
- Manual: legal/compliance override
- All switches timestamped and logged

## Legal Value
- Independent feeds → no bias
- Transparent sourcing → regulatory credibility
- Cryptographic logs → court admissibility
