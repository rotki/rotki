import type { MaybeRef } from 'vue';
import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { AssetPrices } from '@/modules/assets/prices/price-types';
import type { BlockchainAssetBalances, BlockchainBalances } from '@/modules/balances/types/blockchain-balances';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import type { BankConnectionBalances } from '@/modules/banks/types';
import { type BigNumber, bigNumberify, Zero } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { updateAssetValuePrices, updateBankBalancesPrices, updateBlockchainAssetBalances, updateExchangeBalancesPrices } from '@/modules/assets/prices/price-utils';
import { balancesAboveThreshold } from '@/modules/balances/aggregation/core/value-threshold';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

export const useBalancesStore = defineStore('balances', () => {
  const manualBalances = shallowRef<ManualBalanceWithValue[]>([]);
  const manualLiabilities = shallowRef<ManualBalanceWithValue[]>([]);

  const exchangeBalances = shallowRef<ExchangeData>({});
  const exchangeAccountBalances = shallowRef<Record<string, ExchangeData>>({});
  /** What each bank connection holds; banks are a source of their own, never an exchange. */
  const bankBalances = shallowRef<BankConnectionBalances[]>([]);
  const nonFungibleTotalValue = ref<BigNumber>(Zero);

  const blockchainBalances = shallowRef<Balances>({});
  const valueThreshold = useValueThreshold(BalanceSource.BLOCKCHAIN);

  /**
   * The blockchain balances to show, following the hide small balances setting.
   *
   * @remarks
   * `balances` stays complete, because prices are fetched for what it holds and a balance can rise
   * above the threshold once they land. Read it to price or change balances, and this to show them.
   */
  const visibleBalances = computed<Balances>(() => {
    const threshold = get(valueThreshold);
    return threshold === undefined
      ? get(blockchainBalances)
      : balancesAboveThreshold(get(blockchainBalances), bigNumberify(threshold));
  });

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    const latestPrices = get(prices);
    set(blockchainBalances, updateBlockchainAssetBalances(get(blockchainBalances), latestPrices));

    const exchanges = { ...get(exchangeBalances) };
    for (const exchange in exchanges) exchanges[exchange] = updateExchangeBalancesPrices(exchanges[exchange], latestPrices);

    set(exchangeBalances, exchanges);
    const accounts = { ...get(exchangeAccountBalances) };
    for (const [location, balances] of Object.entries(accounts)) {
      accounts[location] = Object.fromEntries(Object.entries(balances).map(([identifier, assets]) => [
        identifier,
        updateExchangeBalancesPrices(assets, latestPrices),
      ]));
    }
    set(exchangeAccountBalances, accounts);
    set(bankBalances, updateBankBalancesPrices(get(bankBalances), latestPrices));

    set(manualBalances, updateAssetValuePrices(get(manualBalances), latestPrices));
    set(manualLiabilities, updateAssetValuePrices(get(manualLiabilities), latestPrices));
  };

  const updateBlockchainBalances = (chain: string, { perAccount }: BlockchainBalances): void => {
    const data = perAccount[camelCase(chain)] ?? {};
    set(blockchainBalances, {
      ...get(blockchainBalances),
      [chain]: data,
    });
  };

  const removeIgnoredAssets = (ignoredAssets: string[]): void => {
    const balances: Balances = { ...get(blockchainBalances) };

    for (const blockchain in balances) {
      const accounts: BlockchainAssetBalances = { ...balances[blockchain] };

      for (const account in accounts) {
        const balance = accounts[account];
        const assets = { ...balance.assets };
        const liabilities = { ...balance.liabilities };

        for (const asset of ignoredAssets) {
          delete assets[asset];
          delete liabilities[asset];
        }

        if (Object.keys(assets).length > 0 || Object.keys(liabilities).length > 0) {
          accounts[account] = {
            assets,
            liabilities,
          };
        }
        else {
          delete accounts[account];
        }
      }

      if (Object.keys(accounts).length === 0) {
        delete balances[blockchain];
      }
      else {
        balances[blockchain] = accounts;
      }
    }

    set(blockchainBalances, balances);
  };

  return {
    balances: blockchainBalances,
    bankBalances,
    exchangeAccountBalances,
    exchangeBalances,
    manualBalances,
    manualLiabilities,
    nonFungibleTotalValue,
    removeIgnoredAssets,
    updateBalances: updateBlockchainBalances,
    updatePrices,
    visibleBalances,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalancesStore, import.meta.hot));
