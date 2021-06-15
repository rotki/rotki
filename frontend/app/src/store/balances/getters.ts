import { default as BigNumber } from 'bignumber.js';
import isEmpty from 'lodash/isEmpty';
import map from 'lodash/map';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import {
  BlockchainAssetBalances,
  SupportedExchange
} from '@/services/balances/types';
import { Balance, GeneralAccountData, HasBalance } from '@/services/types-api';
import {
  AccountAssetBalances,
  AssetBalance,
  AssetBreakdown,
  AssetInfoGetter,
  AssetPriceInfo,
  AssetSymbolGetter,
  BalanceState,
  BlockchainAccountWithBalance,
  BlockchainTotal,
  ExchangeRateGetter,
  IdentifierForSymbolGetter,
  L2Totals,
  LocationBalance,
  BalanceByLocation
} from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { Writeable } from '@/types';
import {
  Blockchain,
  BTC,
  ETH,
  ExchangeInfo,
  GeneralAccount,
  KSM,
  L2_LOOPRING
} from '@/typing/types';
import { assert } from '@/utils/assertions';
import { Zero } from '@/utils/bignumbers';
import { assetSum, balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';

export interface BalanceGetters {
  ethAccounts: BlockchainAccountWithBalance[];
  btcAccounts: BlockchainAccountWithBalance[];
  kusamaBalances: BlockchainAccountWithBalance[];
  totals: AssetBalance[];
  exchangeRate: ExchangeRateGetter;
  exchanges: ExchangeInfo[];
  exchangeBalances: (exchange: string) => AssetBalance[];
  aggregatedBalances: AssetBalance[];
  aggregatedAssets: string[];
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
  assetInfo: AssetInfoGetter;
  assetSymbol: AssetSymbolGetter;
  isEthereumToken: (asset: string) => boolean;
  assetPriceInfo: (asset: string) => AssetPriceInfo;
  breakdown: (asset: string) => AssetBreakdown[];
  loopringBalances: (address: string) => AssetBalance[];
  blockchainAssets: AssetBalance[];
  getIdentifierForSymbol: IdentifierForSymbolGetter;
  byLocation: BalanceByLocation;
  exchangeNonce: (exchange: SupportedExchange) => number;
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
        location: value,
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
    { connectedExchanges, manualBalances, loopringBalances }: BalanceState,
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

    const exchanges = connectedExchanges
      .map(({ location }) => location)
      .filter(uniqueStrings);
    for (const exchange of exchanges) {
      const balances = exchangeBalances(exchange);
      balances.forEach((value: AssetBalance) => addToOwned(value));
    }

    totals.forEach((value: AssetBalance) => addToOwned(value));
    manualBalances.forEach(value => addToOwned(value));

    for (const address in loopringBalances) {
      const balances = loopringBalances[address];
      for (const asset in balances) {
        addToOwned({
          ...balances[asset],
          asset
        });
      }
    }

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
          currentExchangeRate
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
    const aggregateManualBalancesByLocation: BalanceByLocation = simplifyManualBalances.reduce(
      (result: BalanceByLocation, manualBalance: LocationBalance) => {
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

  blockchainTotals: (
    state,
    getters,
    _rootState,
    { status }
  ): BlockchainTotal[] => {
    const sum = (accounts: HasBalance[]): BigNumber => {
      return accounts.reduce((sum: BigNumber, { balance }: HasBalance) => {
        return sum.plus(balance.usdValue);
      }, Zero);
    };

    const totals: BlockchainTotal[] = [];
    const ethAccounts: BlockchainAccountWithBalance[] = getters.ethAccounts;
    const btcAccounts: BlockchainAccountWithBalance[] = getters.btcAccounts;
    const kusamaBalances: BlockchainAccountWithBalance[] =
      getters.kusamaBalances;
    const loopring: AccountAssetBalances = state.loopringBalances;

    if (ethAccounts.length > 0) {
      const ethStatus = status(Section.BLOCKCHAIN_ETH);
      const l2Totals: L2Totals[] = [];
      if (Object.keys(loopring).length > 0) {
        const balances: { [asset: string]: HasBalance } = {};
        for (const address in loopring) {
          for (const asset in loopring[address]) {
            if (!balances[asset]) {
              balances[asset] = {
                balance: loopring[address][asset]
              };
            } else {
              balances[asset] = {
                balance: balanceSum(
                  loopring[address][asset],
                  balances[asset].balance
                )
              };
            }
          }
        }
        const loopringStatus = status(Section.L2_LOOPRING_BALANCES);
        l2Totals.push({
          protocol: L2_LOOPRING,
          usdValue: sum(Object.values(balances)),
          loading:
            loopringStatus === Status.NONE || loopringStatus === Status.LOADING
        });
      }

      totals.push({
        chain: ETH,
        l2: l2Totals.sort((a, b) => b.usdValue.minus(a.usdValue).toNumber()),
        usdValue: sum(ethAccounts),
        loading: ethStatus === Status.NONE || ethStatus === Status.LOADING
      });
    }

    if (btcAccounts.length > 0) {
      const btcStatus = status(Section.BLOCKCHAIN_BTC);
      totals.push({
        chain: BTC,
        l2: [],
        usdValue: sum(btcAccounts),
        loading: btcStatus === Status.NONE || btcStatus === Status.LOADING
      });
    }

    if (kusamaBalances.length > 0) {
      const ksmStatus = status(Section.BLOCKCHAIN_KSM);
      totals.push({
        chain: KSM,
        l2: [],
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

  assetInfo: ({ supportedAssets }: BalanceState) => (identifier: string) => {
    return supportedAssets.find(asset => asset.identifier === identifier);
  },

  accounts: (
    _,
    { ethAccounts, btcAccounts, kusamaBalances }
  ): GeneralAccount[] => {
    return ethAccounts
      .concat(btcAccounts)
      .concat(kusamaBalances)
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
      supportedAsset => supportedAsset.identifier === asset
    );
    if (match) {
      return match.assetType === 'ethereum token';
    }
    return false;
  },
  aggregatedAssets: (_, getters) => {
    const liabilities = getters.liabilities.map(({ asset }) => asset);
    const assets = getters.aggregatedBalances.map(({ asset }) => asset);
    assets.push(...liabilities);
    return assets.filter(uniqueStrings);
  },
  assetPriceInfo: (state, getters1) => asset => {
    const assetValue = getters1.aggregatedBalances.find(
      value => value.asset === asset
    );
    return {
      usdPrice: state.prices[asset] ?? Zero,
      amount: assetValue?.amount ?? Zero,
      usdValue: assetValue?.usdValue ?? Zero
    };
  },
  breakdown: ({
    btc: { standalone, xpubs },
    eth,
    exchangeBalances,
    ksm,
    manualBalances,
    loopringBalances
  }) => asset => {
    const breakdown: AssetBreakdown[] = [];

    for (const exchange in exchangeBalances) {
      const exchangeData = exchangeBalances[exchange];
      if (!exchangeData[asset]) {
        continue;
      }

      breakdown.push({
        address: '',
        location: exchange,
        balance: exchangeData[asset]
      });
    }

    for (let i = 0; i < manualBalances.length; i++) {
      const manualBalance = manualBalances[i];
      if (manualBalance.asset !== asset) {
        continue;
      }
      breakdown.push({
        address: '',
        location: manualBalance.location,
        balance: {
          amount: manualBalance.amount,
          usdValue: manualBalance.usdValue
        }
      });
    }

    for (const address in eth) {
      const ethBalances = eth[address];
      const assetBalance = ethBalances.assets[asset];
      if (!assetBalance) {
        continue;
      }
      breakdown.push({
        address,
        location: ETH,
        balance: assetBalance
      });
    }

    for (const address in loopringBalances) {
      const existing: Writeable<AssetBreakdown> | undefined = breakdown.find(
        value => value.address === address
      );
      const balanceElement = loopringBalances[address][asset];
      if (!balanceElement) {
        continue;
      }
      if (existing) {
        existing.balance = balanceSum(existing.balance, balanceElement);
      } else {
        breakdown.push({
          address,
          location: ETH,
          balance: loopringBalances[address][asset]
        });
      }
    }

    if (asset === BTC) {
      if (standalone) {
        for (const address in standalone) {
          const btcBalance = standalone[address];
          breakdown.push({
            address,
            location: BTC,
            balance: btcBalance
          });
        }
      }

      if (xpubs) {
        for (let i = 0; i < xpubs.length; i++) {
          const xpub = xpubs[i];
          const addresses = xpub.addresses;
          for (const address in addresses) {
            const btcBalance = addresses[address];
            breakdown.push({
              address,
              location: BTC,
              balance: btcBalance
            });
          }
        }
      }
    }

    for (const address in ksm) {
      const balances = ksm[address];
      const assetBalance = balances.assets[asset];
      if (!assetBalance) {
        continue;
      }
      breakdown.push({
        address,
        location: KSM,
        balance: assetBalance
      });
    }

    return breakdown;
  },
  loopringBalances: state => address => {
    const balances: AssetBalance[] = [];
    const loopringBalance = state.loopringBalances[address];
    if (loopringBalance) {
      for (const asset in loopringBalance) {
        balances.push({
          ...loopringBalance[asset],
          asset
        });
      }
    }
    return balances;
  },
  blockchainAssets: (state, { totals }, { session }) => {
    const blockchainTotal = [...totals];
    const ignoredAssets = session!.ignoredAssets;
    const loopringBalances = state.loopringBalances;
    for (const address in loopringBalances) {
      const accountBalances = loopringBalances[address];
      for (const asset in accountBalances) {
        if (ignoredAssets.includes(asset)) {
          continue;
        }
        const existing:
          | Writeable<AssetBalance>
          | undefined = blockchainTotal.find(value => value.asset === asset);
        if (!existing) {
          blockchainTotal.push({
            asset,
            ...accountBalances[asset]
          });
        } else {
          const sum = balanceSum(existing, accountBalances[asset]);
          existing.usdValue = sum.usdValue;
          existing.amount = sum.amount;
        }
      }
    }
    return blockchainTotal;
  },
  getIdentifierForSymbol: state => symbol => {
    const asset = state.supportedAssets.find(asset => asset.symbol === symbol);
    return asset?.identifier;
  },
  assetSymbol: (_bs, { assetInfo }) => identifier => {
    const asset = assetInfo(identifier);
    return asset?.symbol ?? identifier;
  },
  byLocation: (
    state,
    { blockchainTotal, exchanges, manualBalanceByLocation: manual }
  ) => {
    const byLocation: BalanceByLocation = {};

    for (const { location, usdValue } of manual) {
      byLocation[location] = usdValue;
    }

    const blockchain = byLocation[TRADE_LOCATION_BLOCKCHAIN];
    if (blockchain) {
      byLocation[TRADE_LOCATION_BLOCKCHAIN] = blockchain.plus(blockchainTotal);
    } else {
      byLocation[TRADE_LOCATION_BLOCKCHAIN] = blockchainTotal;
    }

    for (const { location, total } of exchanges) {
      const locationElement = byLocation[location];
      if (locationElement) {
        byLocation[location] = locationElement.plus(total);
      } else {
        byLocation[location] = total;
      }
    }

    return byLocation;
  },
  exchangeNonce: ({ connectedExchanges: exchanges }) => exchange => {
    return exchanges.filter(({ location }) => location === exchange).length + 1;
  }
};
