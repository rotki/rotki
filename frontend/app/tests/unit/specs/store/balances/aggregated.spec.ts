import { Blockchain } from '@rotki/common/lib/blockchain';
import { sortBy } from 'lodash-es';
import { expect } from 'vitest';
import { TRADE_LOCATION_BANKS } from '@/data/defaults';
import { useCurrencies } from '@/types/currencies';
import { BalanceType } from '@/types/balances';
import { updateGeneralSettings } from '../../../utils/general-settings';
import type { BlockchainTotals, BtcBalances } from '@/types/blockchain/balances';
import type { AssetBalanceWithPrice } from '@rotki/common';
import type { BitcoinAccounts } from '@/types/blockchain/accounts';
import '../../../i18n';

describe('store::balances/aggregated', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('aggregatedBalances', () => {
    const { exchangeBalances } = storeToRefs(useExchangeBalancesStore());
    const { connectedExchanges } = storeToRefs(useExchangesStore());
    const { prices } = storeToRefs(useBalancePricesStore());
    const { manualBalancesData } = storeToRefs(useManualBalancesStore());
    const { balances } = useAggregatedBalances();
    const { totals: ethTotals } = storeToRefs(useBlockchainStore());

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
        isCurrentCurrency: false,
      },
      EUR: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false,
      },
      SAI: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false,
      },
      ETH: {
        value: bigNumberify(3000),
        isManualPrice: false,
        isCurrentCurrency: false,
      },
      BTC: {
        value: bigNumberify(40000),
        isManualPrice: false,
        isCurrentCurrency: false,
      },
    });

    set(manualBalancesData, [
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

    const totalsState = {
      [Blockchain.ETH]: {
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
      [Blockchain.ETH2]: {},
    };

    set(ethTotals, totalsState);

    const actualResult = sortBy(get(balances()), 'asset');

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
      'asset',
    );

    expect(actualResult).toMatchObject(expectedResult);
  });

  it('btcAccounts', () => {
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

    const { updateAccounts, updateBalances, getBlockchainAccounts, getAccounts } = useBlockchainStore();

    updateAccounts(
      Blockchain.BTC,
      convertBtcAccounts(chain => get(chain).toUpperCase(), Blockchain.BTC, accounts),
    );
    updateBalances(Blockchain.BTC, convertBtcBalances(Blockchain.BTC, totals, btcBalances));

    expect(getBlockchainAccounts(Blockchain.BTC)).toEqual([
      {
        data: {
          derivationPath: 'm',
          xpub: 'xpub123',
        },
        amount: bigNumberify(0),
        chain: Blockchain.BTC,
        expandable: false,
        groupHeader: true,
        groupId: 'xpub123#m#btc',
        label: undefined,
        nativeAsset: 'BTC',
        tags: undefined,
        usdValue: bigNumberify(0),
      },
      {
        data: {
          address: '1234',
        },
        amount: bigNumberify(10),
        usdValue: bigNumberify(10),
        chain: Blockchain.BTC,
        nativeAsset: 'BTC',
        groupId: 'xpub123#m#btc',
        label: undefined,
        expandable: false,
        tags: undefined,
      },
      {
        data: {
          derivationPath: undefined,
          xpub: 'xpub1234',
        },
        amount: bigNumberify(0),
        chain: Blockchain.BTC,
        expandable: false,
        groupHeader: true,
        groupId: 'xpub1234#btc',
        label: '123',
        nativeAsset: 'BTC',
        tags: ['a'],
        usdValue: bigNumberify(0),
      },
      {
        data: {
          address: '123',
        },
        amount: bigNumberify(10),
        usdValue: bigNumberify(10),
        chain: Blockchain.BTC,
        groupId: '123',
        nativeAsset: 'BTC',
        expandable: false,
        label: undefined,
        tags: undefined,
      },
    ]);

    expect(getAccounts(Blockchain.BTC)).toEqual([
      {
        chain: Blockchain.BTC,
        data: {
          derivationPath: 'm',
          xpub: 'xpub123',
        },
        groupHeader: true,
        groupId: 'xpub123#m#btc',
        label: undefined,
        nativeAsset: 'BTC',
        tags: undefined,
      },
      {
        chain: Blockchain.BTC,
        data: {
          address: '1234',
        },
        groupId: 'xpub123#m#btc',
        label: undefined,
        nativeAsset: 'BTC',
        tags: undefined,
      },
      {
        chain: Blockchain.BTC,
        data: {
          derivationPath: undefined,
          xpub: 'xpub1234',
        },
        groupHeader: true,
        groupId: 'xpub1234#btc',
        label: '123',
        nativeAsset: 'BTC',
        tags: ['a'],
      },
      {
        chain: Blockchain.BTC,
        data: {
          address: '123',
        },
        label: undefined,
        nativeAsset: 'BTC',
        tags: undefined,
      },
    ]);
  });

  it('aggregatedBalances, make sure `isCurrentCurrency` do not break the calculation', () => {
    const { exchangeBalances } = storeToRefs(useExchangeBalancesStore());
    const { connectedExchanges } = storeToRefs(useExchangesStore());
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
        isCurrentCurrency: false,
      },
      EUR: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false,
      },
      SAI: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false,
      },
      ETH: {
        value: bigNumberify(3000),
        isManualPrice: false,
        isCurrentCurrency: true,
      },
      BTC: {
        value: bigNumberify(40000),
        isManualPrice: false,
        isCurrentCurrency: false,
      },
    });

    const { manualBalancesData } = storeToRefs(useManualBalancesStore());
    set(manualBalancesData, [
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
    const { totals } = storeToRefs(useBlockchainStore());

    const totalsState = {
      [Blockchain.ETH]: {
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
      [Blockchain.ETH2]: {},
    };

    set(totals, totalsState);
    adjustPrices(get(prices));
    const actualResult = sortBy(get(balances()), 'asset');
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
          usdValue: bigNumberify(375000),
          usdPrice: bigNumberify(3000),
        },
        {
          asset: 'SAI',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100),
          usdPrice: bigNumberify(1),
        },
      ] as AssetBalanceWithPrice[],
      'asset',
    );

    expect(actualResult).toMatchObject(expectedResult);
  });
});
