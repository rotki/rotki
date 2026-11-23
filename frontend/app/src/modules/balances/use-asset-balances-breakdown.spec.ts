import type { AssetBreakdown } from '@/modules/accounts/blockchain-accounts';
import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import { bigNumberify, type Blockchain } from '@rotki/common';
import { createTestExchange, createTestManualBalance } from '@test/utils/create-data';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { testAccounts, testEthereumBalances, testExchangeBalances, testManualBalances } from '@test/utils/test-data';
import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, defineComponent, h, type VNode } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { BalanceType } from '@/modules/balances/types/balances';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { provideHistoryView } from '@/modules/balances/view/balance-view';
import { TRADE_LOCATION_BANKS, TRADE_LOCATION_BLOCKCHAIN, TRADE_LOCATION_EXTERNAL } from '@/modules/core/common/defaults';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

const assetInfoMock = vi.hoisted(() => new Map<string, { isLiability?: boolean }>());

vi.mock('@/modules/assets/use-asset-info-cache', () => ({
  useAssetInfoCache: (): object => ({ resolve: (id: string) => assetInfoMock.get(id) ?? null }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      getChain: () => Blockchain.ETH,
      getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
      getChainName: () => 'Ethereum',
      getEvmChainName: (_chain: string) => 'ethereum',
      getNativeAsset: (chain: Blockchain) => chain,
      isEvmLikeChains: (_chain: string) => false,
      matchChain: (location: string) => (location === 'ethereum' ? Blockchain.ETH : undefined),
      txChains: computed(() => [{
        evmChainName: 'ethereum',
        id: Blockchain.ETH,
        image: '',
        name: 'Ethereum',
        nativeToken: 'ETH',
        type: 'evm',
      } satisfies EvmChainInfo]),
    }),
  };
});

describe('useAssetBalancesBreakdown', () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
    const { exchangeBalances, manualBalances } = storeToRefs(useBalancesStore());
    const { updateAccounts } = useBlockchainAccountsStore();
    const { updateBalances } = useBalancesStore();
    const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
    set(connectedExchanges, [createTestExchange('kraken', 'Kraken 1')]);
    set(manualBalances, testManualBalances);
    set(exchangeBalances, testExchangeBalances);
    updateBalances('eth', testEthereumBalances);
    updateAccounts('eth', testAccounts);
    await nextTick();
  });

  it('should give an accurate breakdown for the asset', () => {
    const { getAssetBreakdown } = useAssetBalancesBreakdown();
    const expectedResult: AssetBreakdown[] = [{
      address: '',
      amount: bigNumberify(2000),
      location: 'kraken',
      tags: undefined,
      value: bigNumberify(2000),
    }, {
      address: '0xaddress2',
      amount: bigNumberify(400),
      location: 'ethereum',
      tags: undefined,
      value: bigNumberify(400),
    }, {
      address: '0xaddress1',
      amount: bigNumberify(300),
      location: 'ethereum',
      tags: undefined,
      value: bigNumberify(300),
    }];

    expect(getAssetBreakdown('GNO')).toMatchObject(expectedResult);
  });

  describe('manual balances', () => {
    beforeEach(() => {
      const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());

      set(manualBalances, [
        createTestManualBalance(
          'DAI',
          50,
          50,
          TRADE_LOCATION_BLOCKCHAIN,
          BalanceType.ASSET,
          1,

        ),
        createTestManualBalance(
          'BTC',
          30,
          30,
          TRADE_LOCATION_BLOCKCHAIN,
          BalanceType.ASSET,
          2,
        ),
      ]);
      set(manualLiabilities, [
        createTestManualBalance(
          'EUR',
          60,
          60,
          TRADE_LOCATION_BANKS,
          BalanceType.LIABILITY,
          3,
        ),
      ]);
    });

    it('should return the breakdown of liabilities', () => {
      const { getAssetBreakdown } = useAssetBalancesBreakdown();
      expect(getAssetBreakdown('EUR', true)).toMatchObject([{
        address: '',
        amount: bigNumberify(60),
        location: TRADE_LOCATION_BANKS,
        tags: undefined,
        value: bigNumberify(60),
      }]);
    });

    it('should return the breakdown of assets', async () => {
      const { getAssetBreakdown, useAssetBreakdown } = useAssetBalancesBreakdown();
      expect(getAssetBreakdown('BTC')).toMatchObject([{
        address: '',
        amount: bigNumberify(30),
        location: TRADE_LOCATION_BLOCKCHAIN,
        tags: undefined,
        value: bigNumberify(30),
      }]);

      expect(getAssetBreakdown('DAI')).toMatchObject([{
        address: '',
        amount: bigNumberify(50),
        location: TRADE_LOCATION_BLOCKCHAIN,
        tags: undefined,
        value: bigNumberify(50),
      }]);

      expect(getAssetBreakdown('EUR')).toMatchObject([]);

      const ethBalances = [
        createTestManualBalance('ETH', 50, 50, TRADE_LOCATION_EXTERNAL, BalanceType.ASSET, 4),
        createTestManualBalance('ETH2', 100, 100, TRADE_LOCATION_EXTERNAL, BalanceType.ASSET, 5),
      ];
      const { manualBalances } = storeToRefs(useBalancesStore());

      set(manualBalances, ethBalances);

      const breakdown = useAssetBreakdown('ETH');

      updateGeneralSettings({
        treatEth2AsEth: false,
      });

      await nextTick();

      expect(get(breakdown)).toMatchObject([{
        address: '',
        amount: bigNumberify(50),
        location: 'external',
        tags: undefined,
        value: bigNumberify(50),
      }]);

      updateGeneralSettings({
        treatEth2AsEth: true,
      });

      expect(get(breakdown)).toMatchObject([{
        address: '',
        amount: bigNumberify(150),
        location: 'external',
        tags: undefined,
        value: bigNumberify(150),
      }]);
    });
  });

  describe('balance view', () => {
    /** Runs the breakdown inside a page that provides the history view, as the dashboard does. */
    function breakdownInHistoryView(
      asset: string,
      liabilities = false,
      filters?: Parameters<ReturnType<typeof useAssetBalancesBreakdown>['getAssetBreakdown']>[2],
    ): AssetBreakdown[] {
      let rows: AssetBreakdown[] = [];
      const Child = defineComponent({
        setup(): () => null {
          rows = useAssetBalancesBreakdown().getAssetBreakdown(asset, liabilities, filters);
          return (): null => null;
        },
      });
      mount(defineComponent({
        setup(): () => VNode {
          provideHistoryView(computed<boolean>(() => true));
          return () => h(Child);
        },
      }));
      return rows;
    }

    const DEBT_TOKEN = 'eip155:1/erc20:0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8';

    beforeEach(() => {
      assetInfoMock.clear();
      assetInfoMock.set(DEBT_TOKEN, { isLiability: true });
      useHistoricalSnapshotStore().setSnapshot({
        entries: [{ amount: bigNumberify(5), asset: 'GNO', location: 'ethereum', locationLabel: '0xaddress1', protocol: null }],
        processingRequired: false,
        stale: false,
      });
    });

    it('should stay queried outside a page that provides the history view, even with history loaded', () => {
      const locations = useAssetBalancesBreakdown().getAssetBreakdown('GNO').map(row => row.location);

      expect(locations).toContain('kraken');
    });

    it('should list the history buckets, without queried exchanges or manual balances, in the history view', () => {
      expect(breakdownInHistoryView('GNO')).toMatchObject([{ address: '0xaddress1', amount: bigNumberify(5), location: 'ethereum' }]);
    });

    it('should leave out history buckets at or below the blockchain small-balance threshold', () => {
      useSettingsRepo().updateFrontend({ balanceValueThreshold: { [BalanceSource.BLOCKCHAIN]: '1000000' } });

      expect(breakdownInHistoryView('GNO')).toStrictEqual([]);
    });

    it('should keep liabilities queried and leave manual liabilities out in the history view', () => {
      const { manualLiabilities } = storeToRefs(useBalancesStore());
      set(manualLiabilities, [createTestManualBalance('GNO', 7, 7, TRADE_LOCATION_EXTERNAL, BalanceType.LIABILITY)]);

      expect(breakdownInHistoryView('GNO', true).map(row => row.location)).not.toContain(TRADE_LOCATION_EXTERNAL);
    });

    function seedDebtToken(liveByAddress: Record<string, number>, historyAmount: number): void {
      useBalancesStore().updateBalances('eth', {
        perAccount: {
          eth: Object.fromEntries(Object.entries(liveByAddress).map(([address, amount]) => [
            address,
            { assets: {}, liabilities: { [DEBT_TOKEN]: { 'aave-v3': { amount: bigNumberify(amount), value: bigNumberify(amount) } } } },
          ])),
        },
        totals: { assets: {}, liabilities: {} },
      });
      useHistoricalSnapshotStore().setSnapshot({
        entries: [{ amount: bigNumberify(historyAmount), asset: DEBT_TOKEN, isLiability: true, location: 'ethereum', locationLabel: '0xaddress1', protocol: null }],
        processingRequired: false,
        stale: false,
      });
    }

    it('should use history liability buckets instead of live liabilities for tracked debt tokens', () => {
      seedDebtToken({ '0xaddress1': 120, '0xaddress2': 80 }, 100);

      expect(breakdownInHistoryView(DEBT_TOKEN, true)).toMatchObject([
        { address: '0xaddress1', amount: bigNumberify(100), location: 'ethereum' },
      ]);
      expect(breakdownInHistoryView(DEBT_TOKEN, true, { groupId: '0xaddress2' })).toStrictEqual([]);
    });

    it('should not fall back to live liabilities when a tracked debt token is filtered out by value threshold', () => {
      seedDebtToken({ '0xaddress1': 500 }, 1);
      useSettingsRepo().updateFrontend({ balanceValueThreshold: { [BalanceSource.BLOCKCHAIN]: '10' } });

      expect(breakdownInHistoryView(DEBT_TOKEN, true)).toStrictEqual([]);
    });

    it('should not fall back to live liabilities when a live debt token has no history bucket', () => {
      seedDebtToken({ '0xaddress1': 500 }, 0);
      useHistoricalSnapshotStore().setSnapshot({
        entries: [{ amount: bigNumberify(5), asset: 'GNO', location: 'ethereum', locationLabel: '0xaddress1', protocol: null }],
        processingRequired: false,
        stale: false,
      });

      expect(breakdownInHistoryView(DEBT_TOKEN, true)).toStrictEqual([]);
    });
  });
});
