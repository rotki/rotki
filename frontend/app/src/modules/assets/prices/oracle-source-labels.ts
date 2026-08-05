import { PriceOracle } from '@/modules/settings/types/price-oracle';

/**
 * What each oracle is called in the UI. Shared by the source chip in a price row and the source
 * pill that filters to it: a filter has to read the same as the rows it produces, and these are
 * brand names rather than anything a casing rule could derive from the id.
 */
const sourceLabels: Record<string, string> = {
  [PriceOracle.ALCHEMY]: 'Alchemy',
  [PriceOracle.BLOCKCHAIN]: 'Blockchain',
  [PriceOracle.COINGECKO]: 'CoinGecko',
  [PriceOracle.CRYPTOCOMPARE]: 'CryptoCompare',
  [PriceOracle.DEFILLAMA]: 'DefiLlama',
  [PriceOracle.FIAT]: 'Fiat',
  [PriceOracle.MANUAL]: 'Manual',
  [PriceOracle.MORALIS]: 'Moralis',
  [PriceOracle.UNISWAP2]: 'Uniswap V2',
  [PriceOracle.UNISWAP3]: 'Uniswap V3',
};

/** An oracle id -> its display name, falling back to the id for one we have no name for. */
export function getOracleSourceLabel(source: string): string {
  return sourceLabels[source] ?? source;
}
