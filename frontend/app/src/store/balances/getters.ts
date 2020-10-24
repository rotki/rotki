import { default as BigNumber } from 'bignumber.js';
import isEmpty from 'lodash/isEmpty';
import map from 'lodash/map';
import { GetterTree } from 'vuex';
import { Balance } from '@/services/types-api';
import {
  BlockchainAccountWithBalance,
  AssetBalance,
  BalanceState,
  ManualBalanceByLocation,
  ManualBalancesByLocation
} from '@/store/balances/types';
import { RotkehlchenState } from '@/store/types';
import { BTC, ETH, GeneralAccount } from '@/typing/types';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { assetSum } from '@/utils/calculation';

export const getters: GetterTree<BalanceState, RotkehlchenState> = {
  ethAccounts({
    eth,
    ethAccounts
  }: BalanceState): BlockchainAccountWithBalance[] {
    const accounts: BlockchainAccountWithBalance[] = [];
    for (const account of ethAccounts) {
      const accountAssets = eth[account.address];
      const balance: Balance = accountAssets
        ? {
            amount: accountAssets.assets.ETH.amount,
            usdValue: accountAssets.totalUsdValue
          }
        : { amount: Zero, usdValue: Zero };

      accounts.push({
        address: account.address,
        label: account.label ?? '',
        tags: account.tags ?? [],
        chain: ETH,
        balance
      });
    }
    return accounts;
  },

  btcAccounts({
    btc,
    btcAccounts
  }: BalanceState): BlockchainAccountWithBalance[] {
    const accounts: BlockchainAccountWithBalance[] = [];

    const { standalone, xpubs } = btcAccounts;
    const zeroBalance = () => ({
      amount: Zero,
      usdValue: Zero
    });

    for (const account of standalone) {
      const balance = btc.standalone?.[account.address] ?? zeroBalance();
      accounts.push({
        address: account.address,
        label: account.label ?? '',
        tags: account.tags ?? [],
        chain: BTC,
        balance
      });
    }

    for (const account of xpubs) {
      accounts.push({
        chain: BTC,
        xpub: account.xpub,
        derivationPath: account.derivationPath ?? '',
        address: '',
        label: account.label ?? '',
        tags: account.tags ?? [],
        balance: zeroBalance()
      });

      if (!account.addresses) {
        continue;
      }

      for (const address of account.addresses) {
        const balanceIndex =
          btc.xpubs?.findIndex(xpub => xpub.addresses[address.address]) ?? -1;
        accounts.push({
          chain: BTC,
          xpub: account.xpub,
          derivationPath: account.derivationPath ?? '',
          address: address.address,
          label: address.label ?? '',
          tags: address.tags ?? [],
          balance:
            balanceIndex > 0
              ? btc.xpubs[balanceIndex].addresses[address.address]
              : zeroBalance()
        });
      }
    }

    return accounts;
  },

  totals(state: BalanceState, _, { session }): AssetBalance[] {
    const ignoredAssets = session!.ignoredAssets;
    return map(state.totals, (value: Balance, asset: string) => {
      const assetBalance: AssetBalance = {
        asset,
        ...value
      };
      return assetBalance;
    }).filter(balance => !ignoredAssets.includes(balance.asset));
  },

  exchangeRate: (state: BalanceState) => (currency: string) => {
    return state.usdToFiatExchangeRates[currency];
  },

  exchanges: (state: BalanceState) => {
    const balances = state.exchangeBalances;
    return Object.keys(balances).map(value => ({
      name: value,
      balances: balances[value],
      total: assetSum(balances[value])
    }));
  },

  exchangeBalances: (state: BalanceState, _, { session }) => (
    exchange: string
  ): AssetBalance[] => {
    const ignoredAssets = session!.ignoredAssets;
    const exchangeBalances = state.exchangeBalances[exchange];
    return exchangeBalances
      ? Object.keys(exchangeBalances)
          .filter(asset => !ignoredAssets.includes(asset))
          .map(
            asset =>
              ({
                asset,
                amount: exchangeBalances[asset].amount,
                usdValue: exchangeBalances[asset].usdValue
              } as AssetBalance)
          )
      : [];
  },

  aggregatedBalances: (
    { connectedExchanges, manualBalances }: BalanceState,
    { exchangeBalances, totals },
    { session }
  ): AssetBalance[] => {
    const ignoredAssets = session!.ignoredAssets;
    const ownedAssets: { [asset: string]: AssetBalance } = {};
    const addToOwned = (value: AssetBalance) => {
      const asset = ownedAssets[value.asset];
      if (ignoredAssets.includes(value.asset)) {
        return;
      }
      ownedAssets[value.asset] = !asset
        ? value
        : {
            asset: asset.asset,
            amount: asset.amount.plus(value.amount),
            usdValue: asset.usdValue.plus(value.usdValue)
          };
    };

    for (const exchange of connectedExchanges) {
      const balances = exchangeBalances(exchange);
      balances.forEach((value: AssetBalance) => addToOwned(value));
    }

    totals.forEach((value: AssetBalance) => addToOwned(value));
    manualBalances.forEach(value => addToOwned(value));
    return Object.values(ownedAssets);
  },

  // simplify the manual balances object so that we can easily reduce it
  manualBalanceByLocation: (
    state: BalanceState,
    { exchangeRate },
    { session }
  ) => {
    const mainCurrency =
      session?.generalSettings.selectedCurrency.ticker_symbol;

    const manualBalances = state.manualBalances;
    const currentExchangeRate = exchangeRate(mainCurrency);

    const simplifyManualBalances = manualBalances.map(perLocationBalance => {
      // because we mix different assets we need to convert them before they are aggregated
      // thus in amount display we always pass the manualBalanceByLocation in the user's main currency
      let convertedValue: BigNumber;
      if (mainCurrency === perLocationBalance.asset) {
        convertedValue = perLocationBalance.amount;
      } else {
        convertedValue = perLocationBalance.usdValue.multipliedBy(
          bigNumberify(currentExchangeRate)
        );
      }

      // to avoid double-conversion, we take as usdValue the amount property when the original asset type and
      // user's main currency coincide
      const { location, usdValue }: ManualBalancesByLocation = {
        location: perLocationBalance.location,
        usdValue: convertedValue
      };
      return { location, usdValue };
    });

    // Aggregate all balances per location
    const aggregateManualBalancesByLocation: ManualBalanceByLocation = simplifyManualBalances.reduce(
      (
        result: ManualBalanceByLocation,
        manualBalance: ManualBalancesByLocation
      ) => {
        if (result[manualBalance.location]) {
          // if the location exists on the reduced object, add the usdValue of the current item to the previous total
          result[manualBalance.location] = result[manualBalance.location].plus(
            manualBalance.usdValue
          );
        } else {
          // otherwise create the location and initiate its value
          result[manualBalance.location] = manualBalance.usdValue;
        }

        return result;
      },
      {}
    );

    return aggregateManualBalancesByLocation;
  },

  blockchainTotal: (_, getters) => {
    return getters.totals.reduce((sum: BigNumber, asset: AssetBalance) => {
      return sum.plus(asset.usdValue);
    }, Zero);
  },

  accountAssets: (state: BalanceState, _, { session }) => (account: string) => {
    const ignoredAssets = session!.ignoredAssets;
    const ethAccount = state.eth[account];
    if (!ethAccount || isEmpty(ethAccount)) {
      return [];
    }

    return Object.entries(ethAccount.assets)
      .filter(([asset]) => !ignoredAssets.includes(asset))
      .map(
        ([key, asset_data]) =>
          ({
            asset: key,
            amount: asset_data.amount,
            usdValue: asset_data.usdValue
          } as AssetBalance)
      );
  },

  hasTokens: (state: BalanceState) => (account: string) => {
    const ethAccount = state.eth[account];
    if (!ethAccount || isEmpty(ethAccount)) {
      return false;
    }

    return Object.entries(ethAccount.assets).length > 1;
  },

  manualLabels: ({ manualBalances }: BalanceState) => {
    return manualBalances.map(value => value.label);
  },

  assetInfo: ({ supportedAssets }: BalanceState) => (key: string) => {
    return supportedAssets.find(asset => asset.key === key);
  },

  accounts: (_, { ethAccounts, btcAccounts }): GeneralAccount[] => {
    return ethAccounts
      .concat(btcAccounts)
      .filter((account: BlockchainAccountWithBalance) => !!account.address)
      .map((account: BlockchainAccountWithBalance) => ({
        chain: account.chain,
        address: account.address,
        label: account.label,
        tags: account.tags
      }));
  },

  account: (_, getters) => (address: string) => {
    const accounts = getters.accounts as GeneralAccount[];
    return accounts.find(acc => acc.address === address);
  },

  isEthereumToken: ({ supportedAssets }) => (asset: string) => {
    const match = supportedAssets.find(
      supportedAsset => supportedAsset.symbol === asset
    );
    if (match) {
      return match.type === 'ethereum token';
    }
    return false;
  }
};
