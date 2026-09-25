import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { createTestBalance, createTestManualBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/modules/core/common/defaults';
import { type BalanceInputs, locationSources } from './location-sources';

const inputs: BalanceInputs = {
  blockchain: {
    eth: { '0x1': { assets: { ETH: { address: createTestBalance(1, 10) } }, liabilities: {} } },
    optimism: { '0x1': { assets: { OP: { address: createTestBalance(2, 2) } }, liabilities: {} } },
  },
  exchanges: { kraken: { BTC: createTestBalance(3, 30) } },
  manual: [
    createTestManualBalance('DAI', 4, 4, 'optimism', BalanceType.ASSET, 1),
    createTestManualBalance('EUR', 5, 5, 'kraken', BalanceType.ASSET, 2),
    createTestManualBalance('USD', 6, 6, TRADE_LOCATION_BLOCKCHAIN, BalanceType.ASSET, 3),
  ],
};

function assetsOf(sources: AssetBalanceEntries[]): string[] {
  return sources.flatMap(source => Object.keys(source)).sort();
}

describe('locationSources', () => {
  it('should read every chain for the blockchain location, with the manual balances placed there', () => {
    expect(assetsOf(locationSources(TRADE_LOCATION_BLOCKCHAIN, inputs, undefined))).toEqual(['ETH', 'OP', 'USD']);
  });

  it('should read only the aliased chain, with the manual balances tagged with the alias', () => {
    expect(assetsOf(locationSources('optimism', inputs, 'optimism'))).toEqual(['DAI', 'OP']);
  });

  it('should read the exchange, with the manual balances tagged with it, for a location that is not a chain', () => {
    expect(assetsOf(locationSources('kraken', inputs, undefined))).toEqual(['BTC', 'EUR']);
  });

  it('should read every chain for the blockchain location even when it also resolves to a chain', () => {
    expect(assetsOf(locationSources(TRADE_LOCATION_BLOCKCHAIN, inputs, 'eth'))).toEqual(['ETH', 'OP', 'USD']);
  });
});
