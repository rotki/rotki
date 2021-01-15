import { default as BigNumber } from 'bignumber.js';
import isEmpty from 'lodash/isEmpty';
import map from 'lodash/map';
import { BlockchainAssetBalances } from '@/services/balances/types';
import { Balance, GeneralAccountData } from '@/services/types-api';
import { SupportedAsset } from '@/services/types-model';
import {
  AccountWithBalance,
  AssetBalance,
  BalanceState,
  BlockchainAccountWithBalance,
  BlockchainTotal,
  LocationBalance,
  ManualBalanceByLocation
} from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import {
  Blockchain,
  BTC,
  ETH,
  ExchangeInfo,
  GeneralAccount,
  KSM
} from '@/typing/types';
import { assert } from '@/utils/assertions';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { assetSum } from '@/utils/calculation';

export interface BalanceGetters {
  ethAccounts: BlockchainAccountWithBalance[];
  btcAccounts: BlockchainAccountWithBalance[];
  kusamaBalances: BlockchainAccountWithBalance[];
  totals: AssetBalance[];
  exchangeRate: (currency: string) => number | undefined;
  exchanges: ExchangeInfo[];
  exchangeBalances: (exchange: string) => AssetBalance[];
  aggregatedBalances: AssetBalance[];
  liabilities: AssetBalance[];
  manualBalanceByLocation: LocationBalance[];
  blockchainTotal: BigNumber;
  blockchainTotals: BlockchainTotal[];
  accountAssets: (account: string) => AssetBalance[];
  accountLiabilities: (account: string) => AssetBalance[];
  hasDetails: (account: string) => boolean;
  manualLabels: string[];
  accounts: GeneralAccount[];
  account: (address: string) => GeneralAccount | undefined;
  assetInfo: (asset: string) => SupportedAsset | undefined;
  isEthereumToken: (asset: string) => boolean;
}

function balances(
  accounts: GeneralAccountData[],
  balances: BlockchainAssetBalances,
  blockchain: Exclude<Blockchain, 'BTC'>
): BlockchainAccountWithBalance[] {
  const data: BlockchainAccountWithBalance[] = [];
  for (const account of accounts) {
    const accountAssets = balances[account.address];

    const balance: Balance = accountAssets
      ? {
          amount: accountAssets.assets[blockchain].amount,
          usdValue: assetSum(accountAssets.assets)
        }
      : { amount: Zero, usdValue: Zero };

    data.push({
      address: account.address,
      label: account.label ?? '',
      tags: account.tags ?? [],
      chain: blockchain,
      balance
    });
  }
  return data;
}

export const getters: Getters<
  BalanceState,
  BalanceGetters,
  RotkehlchenState,
  any
> = {
  ethAccounts({
    eth,
    ethAccounts
  }: BalanceState): BlockchainAccountWithBalance[] {
    return balances(ethAccounts, eth, ETH);
  },
  kusamaBalances: ({ ksmAccounts, ksm }) => {
    return balances(ksmAccounts, ksm, KSM);
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

    for (const { address, label, tags } of standalone) {
      const balance = btc.standalone?.[address] ?? zeroBalance();
      accounts.push({
        address,
        label: label ?? '',
        tags: tags ?? [],
        chain: BTC,
        balance
      });
    }

    for (const { addresses, derivationPath, label, tags, xpub } of xpubs) {
      accounts.push({
        chain: BTC,
        xpub,
        derivationPath: derivationPath ?? '',
        address: '',
        label: label ?? '',
        tags: tags ?? [],
        balance: zeroBalance()
      });

      if (!addresses) {
        continue;
      }

      for (const { address, label, tags } of addresses) {
        const { xpubs } = btc;
        const index = xpubs?.findIndex(xpub => xpub.addresses[address]) ?? -1;
        const balance =
          index >= 0 ? xpubs[index].addresses[address] : zeroBalance();
        accounts.push({
          chain: BTC,
          xpub: xpub,
          derivationPath: derivationPath ?? '',
          address: address,
          label: label ?? '',
          tags: tags ?? [],
          balance: balance
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

  exchanges: (state: BalanceState): ExchangeInfo[] => {
    const balances = state.exchangeBalances;
    return Object.keys(balances)
      .map(value => ({
        name: value,
        balances: balances[value],
        total: assetSum(balances[value])
      }))
      .sort((a, b) => b.total.minus(a.total).toNumber());
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
    return Object.values(ownedAssets).sort((a, b) =>
      b.usdValue.minus(a.usdValue).toNumber()
    );
  },

  liabilities: ({ liabilities }) => {
    return Object.keys(liabilities).map(asset => ({
      asset,
      amount: liabilities[asset].amount,
      usdValue: liabilities[asset].usdValue
    }));
  },

  // simplify the manual balances object so that we can easily reduce it
  manualBalanceByLocation: (
    state: BalanceState,
    { exchangeRate },
    { session }
  ): LocationBalance[] => {
    const mainCurrency =
      session?.generalSettings.selectedCurrency.ticker_symbol;

    assert(mainCurrency, 'main currency was not properly set');

    const manualBalances = state.manualBalances;
    const currentExchangeRate = exchangeRate(mainCurrency);
    if (currentExchangeRate === undefined) {
      return [];
    }
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
      const { location, usdValue }: LocationBalance = {
        location: perLocationBalance.location,
        usdValue: convertedValue
      };
      return { location, usdValue };
    });

    // Aggregate all balances per location
    const aggregateManualBalancesByLocation: ManualBalanceByLocation = simplifyManualBalances.reduce(
      (result: ManualBalanceByLocation, manualBalance: LocationBalance) => {
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

    return Object.keys(aggregateManualBalancesByLocation)
      .map(location => ({
        location,
        usdValue: aggregateManualBalancesByLocation[location]
      }))
      .sort((a, b) => b.usdValue.minus(a.usdValue).toNumber());
  },

  blockchainTotal: (_, getters) => {
    return getters.totals.reduce((sum: BigNumber, asset: AssetBalance) => {
      return sum.plus(asset.usdValue);
    }, Zero);
  },

  blockchainTotals: (_, getters, _rootState, { status }): BlockchainTotal[] => {
    const sum = (accounts: BlockchainAccountWithBalance[]): BigNumber => {
      return accounts.reduce(
        (sum: BigNumber, { balance }: AccountWithBalance) => {
          return sum.plus(balance.usdValue);
        },
        Zero
      );
    };

    const totals: BlockchainTotal[] = [];
    const ethAccounts: BlockchainAccountWithBalance[] = getters.ethAccounts;
    const btcAccounts: BlockchainAccountWithBalance[] = getters.btcAccounts;
    const kusamaBalances: BlockchainAccountWithBalance[] =
      getters.kusamaBalances;

    if (ethAccounts.length > 0) {
      const ethStatus = status(Section.BLOCKCHAIN_ETH);
      totals.push({
        chain: ETH,
        usdValue: sum(ethAccounts),
        loading: ethStatus === Status.NONE || ethStatus === Status.LOADING
      });
    }

    if (btcAccounts.length > 0) {
      const btcStatus = status(Section.BLOCKCHAIN_BTC);
      totals.push({
        chain: BTC,
        usdValue: sum(btcAccounts),
        loading: btcStatus === Status.NONE || btcStatus === Status.LOADING
      });
    }

    if (kusamaBalances.length > 0) {
      const ksmStatus = status(Section.BLOCKCHAIN_KSM);
      totals.push({
        chain: KSM,
        usdValue: sum(kusamaBalances),
        loading: ksmStatus === Status.NONE || ksmStatus === Status.LOADING
      });
    }

    return totals.sort((a, b) => b.usdValue.minus(a.usdValue).toNumber());
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

  accountLiabilities: (state: BalanceState, _, { session }) => (
    account: string
  ) => {
    const ignoredAssets = session!.ignoredAssets;
    const ethAccount = state.eth[account];
    if (!ethAccount || isEmpty(ethAccount)) {
      return [];
    }

    return Object.entries(ethAccount.liabilities)
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

  hasDetails: (state: BalanceState) => (account: string) => {
    const ethAccount = state.eth[account];
    if (!ethAccount || isEmpty(ethAccount)) {
      return false;
    }

    const assets = Object.entries(ethAccount.assets);
    const liabilities = Object.entries(ethAccount.liabilities);
    return assets.length > 1 || liabilities.length > 1;
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
