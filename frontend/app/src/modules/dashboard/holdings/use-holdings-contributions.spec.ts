import { bigNumberify } from '@rotki/common';
import { createTestBalance, createTestExchange, createTestManualBalance, createTestPriceInfo } from '@test/utils/create-data';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { BalanceType } from '@/modules/balances/types/balances';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { summarizeSources } from '@/modules/dashboard/holdings/core/source-summary';
import { useHoldingsContributions } from '@/modules/dashboard/holdings/use-holdings-contributions';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';
import '@test/i18n';

vi.mock('@/modules/core/common/use-supported-chains', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/core/common/use-supported-chains')>();
  return {
    ...actual,
    useSupportedChains: vi.fn().mockImplementation(() => ({
      ...actual.useSupportedChains(),
      matchChain: (location: string): string | undefined => (location === 'ethereum' ? 'eth' : undefined),
    })),
  };
});

vi.mock('@/modules/assets/amount-display/use-number-scrambler', () => ({
  useNumberScrambler: vi.fn(({ value }) => value),
}));

/**
 * One account per chain holding what the fixture needs: ETH on `eth`, a validator on `eth2`, and an
 * asset the user ignores, so each part of the net worth formula is exercised.
 */
function seedStores(): void {
  const { balances, exchangeBalances, manualBalances, manualLiabilities, nonFungibleTotalValue } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { prices } = storeToRefs(useBalancePricesStore());
  const { allLocations } = storeToRefs(useLocationStore());
  const { ignoredAssets } = storeToRefs(useAssetsStore());

  set(allLocations, {
    ethereum: { isExchange: false, label: 'Ethereum' },
    external: { isExchange: false, label: 'External' },
    kraken: { isExchange: true, label: 'Kraken' },
  });
  set(ignoredAssets, ['SPAM']);
  set(prices, {
    BTC: createTestPriceInfo(40000),
    DAI: createTestPriceInfo(1),
    ETH: createTestPriceInfo(3000),
    SPAM: createTestPriceInfo(10),
  });
  set(balances, {
    eth: {
      '0xA': {
        assets: {
          DAI: { address: createTestBalance(500, 500) },
          ETH: { address: createTestBalance(2, 6000) },
          SPAM: { address: createTestBalance(1000, 10000) },
        },
        liabilities: {},
      },
    },
    eth2: {
      '0xV': { assets: { ETH: { address: createTestBalance(32, 96000) } }, liabilities: {} },
    },
  });
  set(connectedExchanges, [createTestExchange('kraken', 'Kraken')]);
  set(exchangeBalances, { kraken: { BTC: createTestBalance(0.5, 20000) } });
  set(manualBalances, [
    createTestManualBalance('DAI', 300, 300, 'external', BalanceType.ASSET, 1),
    createTestManualBalance('DAI', 50, 50, 'ethereum', BalanceType.ASSET, 2),
    createTestManualBalance('SPAM', 5, 50, 'external', BalanceType.ASSET, 3),
  ]);
  set(manualLiabilities, [createTestManualBalance('DAI', 1000, 1000, 'external', BalanceType.LIABILITY, 4)]);
  set(nonFungibleTotalValue, bigNumberify(700));
}

describe('useHoldingsContributions', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    seedStores();
  });

  it('should add up, minus liabilities, to the net worth headline', () => {
    useSettingsRepo().updateFrontend({ nftsInNetValue: true });
    const { contributions, liabilities, nfts } = useHoldingsContributions();

    const summary = summarizeSources(get(contributions), { liabilities: get(liabilities), nfts: get(nfts) });

    expect(summary.gross.minus(summary.liabilities).toFixed()).toBe(get(storeToRefs(useStatisticsStore()).totalNetWorth).toFixed());
  });

  it('should leave NFTs out when they do not count toward net worth, and still add up', () => {
    useSettingsRepo().updateFrontend({ nftsInNetValue: false });
    const { contributions, liabilities, nfts } = useHoldingsContributions();

    const summary = summarizeSources(get(contributions), { liabilities: get(liabilities), nfts: get(nfts) });

    expect(get(nfts)).toBeUndefined();
    expect(summary.gross.minus(summary.liabilities).toFixed()).toBe(get(storeToRefs(useStatisticsStore()).totalNetWorth).toFixed());
  });

  it('should report one contribution per chain, source location and manual balance, without ignored assets', () => {
    const { contributions } = useHoldingsContributions();

    expect(get(contributions).map(contribution => ({
      at: contribution.kind === SourceKind.BLOCKCHAIN ? contribution.chain : contribution.location,
      kind: contribution.kind,
      value: contribution.value.toFixed(),
    }))).toEqual([
      { at: 'eth', kind: 'blockchain', value: '6500' },
      { at: 'eth2', kind: 'blockchain', value: '96000' },
      { at: 'kraken', kind: 'exchange', value: '20000' },
      { at: 'external', kind: 'manual', value: '300' },
      { at: 'ethereum', kind: 'manual', value: '50' },
    ]);
  });

  it('should place a chain under its trade location, and a chain with none under nothing', () => {
    const { locationOfChain } = useHoldingsContributions();

    expect(locationOfChain('eth')).toBe('ethereum');
    expect(locationOfChain('eth2')).toBeUndefined();
  });
});
