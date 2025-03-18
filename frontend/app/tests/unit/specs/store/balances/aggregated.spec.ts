import type { BitcoinAccounts, BlockchainAccountGroupWithBalance } from '@/types/blockchain/accounts';
import type { BlockchainTotals, BtcBalances } from '@/types/blockchain/balances';
import { useBalances } from '@/composables/balances';
import { useAggregatedBalances } from '@/composables/balances/aggregated';
import { TRADE_LOCATION_BANKS } from '@/data/defaults';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useBlockchainStore } from '@/store/blockchain';
import { useSessionSettingsStore } from '@/store/settings/session';
import { BalanceType } from '@/types/balances';
import { useCurrencies } from '@/types/currencies';
import { convertBtcAccounts, convertBtcBalances } from '@/utils/blockchain/accounts';
import { type AssetBalanceWithPrice, bigNumberify, Blockchain, Zero } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { sortBy } from 'es-toolkit';
import { beforeEach, describe, expect, it } from 'vitest';
import '../../../i18n';

describe('store::balances/aggregated', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('aggregatedBalances', () => {
    const { exchangeBalances, manualBalances } = storeToRefs(useBalancesStore());
    const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
    const { prices } = storeToRefs(useBalancePricesStore());
    const { balances } = useAggregatedBalances();
    const { balances: ethBalances } = storeToRefs(useBlockchainStore());

    set(connectedExchanges, [
      {
        location: 'kraken',
        name: 'Bitrex Acc',
      },
    ]);

    set(exchangeBalances, {
      kraken: {
        DAI: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
        },
        BTC: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
        },
        ETH: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
        },
        EUR: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
        },
      },
    });

    set(prices, {
      DAI: {
        value: bigNumberify(1),
        isManualPrice: false,
      },
      EUR: {
        value: bigNumberify(1),
        isManualPrice: false,
      },
      SAI: {
        value: bigNumberify(1),
        isManualPrice: false,
      },
      ETH: {
        value: bigNumberify(3000),
        isManualPrice: false,
      },
      BTC: {
        value: bigNumberify(40000),
        isManualPrice: false,
      },
    });

    set(manualBalances, [
      {
        identifier: 1,
        usdValue: bigNumberify(50),
        amount: bigNumberify(50),
        asset: 'DAI',
        label: '123',
        tags: [],
        location: TRADE_LOCATION_BANKS,
        balanceType: BalanceType.ASSET,
      },
    ]);

    set(ethBalances, {
      [Blockchain.ETH.toString()]: {
        '0x123': {
          assets: {
            DAI: {
              amount: bigNumberify(100),
              usdValue: bigNumberify(100),
            },
            BTC: {
              amount: bigNumberify(100),
              usdValue: bigNumberify(100),
            },
            ETH: {
              amount: bigNumberify(100),
              usdValue: bigNumberify(100),
            },
            SAI: {
              amount: bigNumberify(100),
              usdValue: bigNumberify(100),
            },
          },
          liabilities: {},
        },
      },
    });

    const actualResult = sortBy(get(balances()), ['asset']);

    const expectedResult = sortBy(
      [
        {
          asset: 'EUR',
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
          usdPrice: bigNumberify(1),
        },
        {
          asset: 'DAI',
          amount: bigNumberify(200),
          usdValue: bigNumberify(200),
          usdPrice: bigNumberify(1),
        },
        {
          asset: 'BTC',
          amount: bigNumberify(150),
          usdValue: bigNumberify(150),
          usdPrice: bigNumberify(40000),
        },
        {
          asset: 'ETH',
          amount: bigNumberify(150),
          usdValue: bigNumberify(150),
          usdPrice: bigNumberify(3000),
        },
        {
          asset: 'SAI',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100),
          usdPrice: bigNumberify(1),
        },
      ] satisfies AssetBalanceWithPrice[],
      ['asset'],
    );

    expect(actualResult).toMatchObject(expectedResult);
  });

  it('btcAccounts', async () => {
    const accounts: BitcoinAccounts = {
      standalone: [
        {
          address: '123',
          tags: null,
          label: null,
        },
      ],
      xpubs: [
        {
          xpub: 'xpub123',
          addresses: [
            {
              address: '1234',
              tags: null,
              label: null,
            },
          ],
          tags: null,
          label: null,
          derivationPath: 'm',
        },
        {
          xpub: 'xpub1234',
          derivationPath: null,
          label: '123',
          tags: ['a'],
          addresses: null,
        },
      ],
    };
    const btcBalances: BtcBalances = {
      standalone: {
        123: { usdValue: bigNumberify(10), amount: bigNumberify(10) },
      },
      xpubs: [
        {
          xpub: 'xpub123',
          derivationPath: 'm',
          addresses: {
            1234: { usdValue: bigNumberify(10), amount: bigNumberify(10) },
          },
        },
      ],
    };

    const totals: BlockchainTotals = {
      assets: {
        [Blockchain.BTC.toUpperCase()]: {
          usdValue: bigNumberify(20),
          amount: bigNumberify(20),
        },
      },
      liabilities: {},
    };

    const { updateAccounts, updateBalances, getBlockchainAccounts, fetchAccounts } = useBlockchainStore();

    updateAccounts(
      Blockchain.BTC,
      convertBtcAccounts(chain => get(chain).toUpperCase(), Blockchain.BTC, accounts),
    );
    updateBalances(Blockchain.BTC, convertBtcBalances(Blockchain.BTC, totals, btcBalances));

    expect(getBlockchainAccounts(Blockchain.BTC)).toEqual([
      {
        type: 'account',
        data: {
          type: 'address',
          address: '1234',
        },
        amount: bigNumberify(10),
        usdValue: bigNumberify(10),
        chain: Blockchain.BTC,
        nativeAsset: 'BTC',
        groupId: 'xpub123#m#btc',
        label: undefined,
        expansion: undefined,
        tags: undefined,
      },
      {
        type: 'account',
        data: {
          type: 'address',
          address: '123',
        },
        amount: bigNumberify(10),
        usdValue: bigNumberify(10),
        chain: Blockchain.BTC,
        groupId: '123',
        nativeAsset: 'BTC',
        expansion: undefined,
        label: undefined,
        tags: undefined,
      },
    ]);

    const knownGroups = await fetchAccounts({ limit: 10, offset: 0 });

    const chain = Blockchain.BTC.toString();

    const groups: BlockchainAccountGroupWithBalance[] = [
      {
        type: 'group',
        data: {
          type: 'address',
          address: '123',
        },
        usdValue: bigNumberify(10),
        chains: [chain],
        label: '123',
        tags: undefined,
      },
      {
        type: 'group',
        data: {
          type: 'xpub',
          xpub: 'xpub123',
          derivationPath: 'm',
        },
        nativeAsset: 'BTC',
        chains: [chain],
        expansion: 'accounts',
        label: undefined,
        tags: undefined,
        amount: bigNumberify(10),
        usdValue: bigNumberify(10),
      },
      {
        type: 'group',
        data: {
          type: 'xpub',
          xpub: 'xpub1234',
          derivationPath: undefined,
        },
        amount: Zero,
        usdValue: Zero,
        nativeAsset: 'BTC',
        chains: [chain],
        label: '123',
        tags: ['a'],
      },
    ];

    expect(knownGroups.data).toEqual(groups);
  });

  it('aggregatedBalances, make sure `isCurrentCurrency` do not break the calculation', () => {
    const { exchangeBalances } = storeToRefs(useBalancesStore());
    const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
    set(connectedExchanges, [
      {
        location: 'kraken',
        name: 'Bitrex Acc',
      },
    ]);

    set(exchangeBalances, {
      kraken: {
        DAI: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
        },
        BTC: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
        },
        ETH: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
        },
        EUR: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
        },
      },
    });

    const { prices } = storeToRefs(useBalancePricesStore());
    const { adjustPrices } = useBalances();

    const { exchangeRates } = storeToRefs(useBalancePricesStore());
    set(exchangeRates, { EUR: bigNumberify(1.2) });

    const { currencies } = useCurrencies();
    updateGeneralSettings({
      mainCurrency: get(currencies)[1],
    });

    set(prices, {
      DAI: {
        value: bigNumberify(1),
        isManualPrice: false,
      },
      EUR: {
        value: bigNumberify(1),
        isManualPrice: false,
      },
      SAI: {
        value: bigNumberify(1),
        isManualPrice: false,
      },
      ETH: {
        value: bigNumberify(3000),
        isManualPrice: false,
      },
      BTC: {
        value: bigNumberify(40000),
        isManualPrice: false,
      },
    });

    const { manualBalances } = storeToRefs(useBalancesStore());
    set(manualBalances, [
      {
        identifier: 1,
        usdValue: bigNumberify(50),
        amount: bigNumberify(50),
        asset: 'DAI',
        label: '123',
        tags: [],
        location: TRADE_LOCATION_BANKS,
        balanceType: BalanceType.ASSET,
      },
    ]);

    const { balances } = useAggregatedBalances();
    const { balances: allBalances } = storeToRefs(useBlockchainStore());

    set(allBalances, {
      [Blockchain.ETH]: {
        '0x123': {
          assets: {
            DAI: {
              amount: bigNumberify(100),
              usdValue: bigNumberify(100),
            },
            BTC: {
              amount: bigNumberify(100),
              usdValue: bigNumberify(100),
            },
            ETH: {
              amount: bigNumberify(100),
              usdValue: bigNumberify(100),
            },
            SAI: {
              amount: bigNumberify(100),
              usdValue: bigNumberify(100),
            },
          },
          liabilities: {},
        },
      },
    });
    adjustPrices(get(prices));
    const actualResult = sortBy(get(balances()), ['asset']);
    const expectedResult = sortBy(
      [
        {
          asset: 'EUR',
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
          usdPrice: bigNumberify(1),
        },
        {
          asset: 'DAI',
          amount: bigNumberify(200),
          usdValue: bigNumberify(200),
          usdPrice: bigNumberify(1),
        },
        {
          asset: 'BTC',
          amount: bigNumberify(150),
          usdValue: bigNumberify(6000000),
          usdPrice: bigNumberify(40000),
        },
        {
          asset: 'ETH',
          amount: bigNumberify(150),
          usdValue: bigNumberify(450000),
          usdPrice: bigNumberify(3000),
        },
        {
          asset: 'SAI',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100),
          usdPrice: bigNumberify(1),
        },
      ] as AssetBalanceWithPrice[],
      ['asset'],
    );

    expect(actualResult).toMatchObject(expectedResult);
  });
});
