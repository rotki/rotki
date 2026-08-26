/**
 * What each oracle is called in the UI. Shared by the source chip in a price row and the source
 * pill that filters to it: a filter has to read the same as the rows it produces, and these are
 * brand names rather than anything a casing rule could derive from the id.
 *
 * These are the backend's `HistoricalPriceOracle` members, NOT the `PriceOracle` list the settings
 * use. The two overlap but are not the same, and only an oracle that can be a
 * `price_history.source_type` belongs here — borrowing `blockchain` or `fiat` from `PriceOracle`
 * makes the endpoint answer `source_type blockchain is not stored in price_history`.
 *
 * The keys are wire values, which the backend derives from the enum member name — hence
 * `manual current` with a space rather than the `manualcurrent` the settings enum uses.
 */
const sourceLabels: Record<string, string> = {
  'alchemy': 'Alchemy',
  'coingecko': 'CoinGecko',
  'coinbase': 'Coinbase',
  'cryptocompare': 'CryptoCompare',
  'defillama': 'DefiLlama',
  'manual': 'Manual',
  'manual current': 'Manual (current)',
  'moralis': 'Moralis',
  'uniswapv2': 'Uniswap V2',
  'uniswapv3': 'Uniswap V3',
  'xratescom': 'x-rates.com',
};

/** Maps an oracle id to its display name, falling back to the id when there is no name for it. */
export function getOracleSourceLabel(source: string): string {
  return sourceLabels[source] ?? source;
}

/**
 * The oracles the source filter offers, derived from the labels above rather than listed again:
 * an oracle the filter offers but has no name for would show its raw id on the pill.
 */
export const ORACLE_SOURCES: string[] = Object.keys(sourceLabels);
