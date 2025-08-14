import type { EvmChainInfo } from '@/types/api/chains';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import { bigNumberify, type Blockchain } from '@rotki/common';
import { createTestManualBalance } from '@test/utils/create-data';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { testAccounts, testEthereumBalances, testExchangeBalances, testManualBalances } from '@test/utils/test-data';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TRADE_LOCATION_BANKS, TRADE_LOCATION_BLOCKCHAIN, TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useSessionSettingsStore } from '@/store/settings/session';
import { BalanceType } from '@/types/balances';

vi.mock('@/composables/info/chains', async () => {
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
    const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
    set(connectedExchanges, [{
      location: 'kraken',
      name: 'Kraken 1',
    }]);
    set(manualBalances, testManualBalances);
    set(exchangeBalances, testExchangeBalances);
    updateBalances('eth', testEthereumBalances);
    updateAccounts('eth', testAccounts);
    await nextTick();
  });

  it('should give an accurate breakdown for the asset', () => {
    const { useAssetBreakdown } = useAssetBalancesBreakdown();
    const assetBreakdown = useAssetBreakdown('GNO');
    const expectedResult: AssetBreakdown[] = [{
      address: '',
      amount: bigNumberify(2000),
      location: 'kraken',
      tags: undefined,
      usdValue: bigNumberify(2000),
    }, {
      address: '0xaddress2',
      amount: bigNumberify(400),
      location: 'ethereum',
      tags: undefined,
      usdValue: bigNumberify(400),
    }, {
      address: '0xaddress1',
      amount: bigNumberify(300),
      location: 'ethereum',
      tags: undefined,
      usdValue: bigNumberify(300),
    }];

    expect(get(assetBreakdown)).toMatchObject(expectedResult);
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
      const { useAssetBreakdown } = useAssetBalancesBreakdown();
      expect(get(useAssetBreakdown('EUR', true))).toMatchObject([{
        address: '',
        amount: bigNumberify(60),
        location: TRADE_LOCATION_BANKS,
        tags: undefined,
        usdValue: bigNumberify(60),
      }]);
    });

    it('should return the breakdown of assets', async () => {
      const { useAssetBreakdown } = useAssetBalancesBreakdown();
      expect(get(useAssetBreakdown('BTC'))).toMatchObject([{
        address: '',
        amount: bigNumberify(30),
        location: TRADE_LOCATION_BLOCKCHAIN,
        tags: undefined,
        usdValue: bigNumberify(30),
      }]);

      expect(get(useAssetBreakdown('DAI'))).toMatchObject([{
        address: '',
        amount: bigNumberify(50),
        location: TRADE_LOCATION_BLOCKCHAIN,
        tags: undefined,
        usdValue: bigNumberify(50),
      }]);

      // Breakdown for liabilities
      expect(get(useAssetBreakdown('EUR'))).toMatchObject([]);

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
        usdValue: bigNumberify(50),
      }]);

      updateGeneralSettings({
        treatEth2AsEth: true,
      });

      expect(get(breakdown)).toMatchObject([{
        address: '',
        amount: bigNumberify(150),
        location: 'external',
        tags: undefined,
        usdValue: bigNumberify(150),
      }]);
    });
  });
});
