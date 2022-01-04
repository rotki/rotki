import {
  AssetBalance,
  AssetBalanceWithPrice,
  Balance,
  BigNumber,
  HasBalance
} from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { SupportedAsset } from '@rotki/common/lib/data';
import isEmpty from 'lodash/isEmpty';
import map from 'lodash/map';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { BlockchainAssetBalances } from '@/services/balances/types';
import { GeneralAccountData } from '@/services/types-api';
import {
  AccountAssetBalances,
  AssetBreakdown,
  AssetInfoGetter,
  AssetPriceInfo,
  AssetSymbolGetter,
  BalanceByLocation,
  BalanceState,
  BlockchainAccountWithBalance,
  BlockchainTotal,
  ExchangeRateGetter,
  IdentifierForSymbolGetter,
  L2Totals,
  LocationBalance,
  NonFungibleBalance
} from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { Writeable } from '@/types';
import { ExchangeInfo, SupportedExchange } from '@/types/exchanges';
import { L2_LOOPRING } from '@/types/protocols';
import { ReadOnlyTag } from '@/types/user';
import { assert } from '@/utils/assertions';
import { Zero } from '@/utils/bignumbers';
import { assetSum, balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';

export interface BalanceGetters {
  ethAccounts: BlockchainAccountWithBalance[];
  eth2Balances: BlockchainAccountWithBalance[];
  ethAddresses: string[];
  btcAccounts: BlockchainAccountWithBalance[];
  kusamaBalances: BlockchainAccountWithBalance[];
  avaxAccounts: BlockchainAccountWithBalance[];
  polkadotBalances: BlockchainAccountWithBalance[];
  loopringAccounts: BlockchainAccountWithBalance[];
  totals: AssetBalance[];
  exchangeRate: ExchangeRateGetter;
  exchanges: ExchangeInfo[];
  exchangeBalances: (exchange: string) => AssetBalance[];
  aggregatedBalances: AssetBalanceWithPrice[];
  aggregatedAssets: string[];
  liabilities: AssetBalanceWithPrice[];
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
  blockchainAssets: AssetBalanceWithPrice[];
  getIdentifierForSymbol: IdentifierForSymbolGetter;
  byLocation: BalanceByLocation;
  exchangeNonce: (exchange: SupportedExchange) => number;
  nfTotalValue: BigNumber;
  nfBalances: NonFungibleBalance[];
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
    ethAccounts,
    loopringBalances
  }: BalanceState): BlockchainAccountWithBalance[] {
    const accounts = balances(ethAccounts, eth, Blockchain.ETH);

    // check if account is loopring account
    return accounts.map(ethAccount => {
      const address = ethAccount.address;
      const balances = loopringBalances[address];
      const tags = ethAccount.tags || [];
      if (balances) {
        tags.push(ReadOnlyTag.LOOPRING);
      }

      return { ...ethAccount, tags: tags.filter(uniqueStrings) };
    });
  },
  eth2Balances({
    eth2,
    eth2Validators
  }: BalanceState): BlockchainAccountWithBalance[] {
    const balances: BlockchainAccountWithBalance[] = [];
    for (const {
      publicKey,
      validatorIndex,
      ownershipPercentage
    } of eth2Validators.entries) {
      const validatorBalances = eth2[publicKey];
      let balance: Balance = { amount: Zero, usdValue: Zero };
      if (validatorBalances && validatorBalances.assets) {
        const assets = validatorBalances.assets;
        balance = {
          amount: assets[Blockchain.ETH2].amount,
          usdValue: assetSum(assets)
        };
      }
      balances.push({
        address: publicKey,
        chain: Blockchain.ETH2,
        balance,
        label: validatorIndex.toString() ?? '',
        tags: [],
        ownershipPercentage
      });
    }
    return balances;
  },
  ethAddresses: ({ ethAccounts }) => {
    return ethAccounts.map(({ address }) => address);
  },
  kusamaBalances: ({ ksmAccounts, ksm }) => {
    return balances(ksmAccounts, ksm, Blockchain.KSM);
  },

  avaxAccounts: ({
    avaxAccounts,
    avax
  }: BalanceState): BlockchainAccountWithBalance[] => {
    return balances(avaxAccounts, avax, Blockchain.AVAX);
  },
  polkadotBalances: ({ dotAccounts, dot }) => {
    return balances(dotAccounts, dot, Blockchain.DOT);
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
        chain: Blockchain.BTC,
        balance
      });
    }

    for (const { addresses, derivationPath, label, tags, xpub } of xpubs) {
      accounts.push({
        chain: Blockchain.BTC,
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
        if (!xpubs) {
          continue;
        }
        const index = xpubs.findIndex(xpub => xpub.addresses[address]) ?? -1;
        const balance =
          index >= 0 ? xpubs[index].addresses[address] : zeroBalance();
        accounts.push({
          chain: Blockchain.BTC,
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
  loopringAccounts({
    loopringBalances,
    ethAccounts
  }): BlockchainAccountWithBalance[] {
    const accounts: BlockchainAccountWithBalance[] = [];
    for (const address in loopringBalances) {
      const assets = loopringBalances[address];

      const tags =
        ethAccounts.find(account => account.address === address)?.tags || [];

      const balance = {
        amount: Zero,
        usdValue: Zero
      };

      for (const asset in assets) {
        const assetBalance = assets[asset];

        balance.amount = balance.amount.plus(assetBalance.amount);
        balance.usdValue = balance.usdValue.plus(assetBalance.usdValue);
      }

      accounts.push({
        address,
        balance,
        chain: Blockchain.ETH,
        label: '',
        tags: [...tags, ReadOnlyTag.LOOPRING].filter(uniqueStrings)
      });
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

  exchangeBalances:
    (state: BalanceState, _, { session }) =>
    (exchange: string): AssetBalance[] => {
      const ignoredAssets = session!.ignoredAssets;
      const exchangeBalances = state.exchangeBalances[exchange];
      const noPrice = new BigNumber(-1);
      return exchangeBalances
        ? Object.keys(exchangeBalances)
            .filter(asset => !ignoredAssets.includes(asset))
            .map(
              asset =>
                ({
                  asset,
                  amount: exchangeBalances[asset].amount,
                  usdValue: exchangeBalances[asset].usdValue,
                  usdPrice: state.prices[asset] ?? noPrice
                } as AssetBalance)
            )
        : [];
    },

  aggregatedBalances: (
    {
      connectedExchanges,
      manualBalances,
      loopringBalances,
      prices
    }: BalanceState,
    { exchangeBalances, totals },
    { session }
  ): AssetBalanceWithPrice[] => {
    const ignoredAssets = session!.ignoredAssets;
    const ownedAssets: { [asset: string]: AssetBalanceWithPrice } = {};
    const addToOwned = (value: AssetBalance) => {
      const asset = ownedAssets[value.asset];
      if (ignoredAssets.includes(value.asset)) {
        return;
      }
      ownedAssets[value.asset] = !asset
        ? {
            ...value,
            usdPrice: prices[value.asset] ?? new BigNumber(-1)
          }
        : {
            asset: asset.asset,
            amount: asset.amount.plus(value.amount),
            usdValue: asset.usdValue.plus(value.usdValue),
            usdPrice: prices[asset.asset] ?? new BigNumber(-1)
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

  liabilities: ({ liabilities, manualLiabilities, prices }) => {
    const noPrice = new BigNumber(-1);
    const liabilitiesMerged: Record<string, Balance> = { ...liabilities };
    for (const { amount, asset, usdValue } of manualLiabilities) {
      const liability = liabilitiesMerged[asset];
      if (liability) {
        liabilitiesMerged[asset] = {
          amount: liability.amount.plus(amount),
          usdValue: liability.usdValue.plus(usdValue)
        };
      } else {
        liabilitiesMerged[asset] = {
          amount: amount,
          usdValue: usdValue
        };
      }
    }
    return Object.keys(liabilitiesMerged).map(asset => ({
      asset,
      amount: liabilitiesMerged[asset].amount,
      usdValue: liabilitiesMerged[asset].usdValue,
      usdPrice: prices[asset] ?? noPrice
    }));
  },

  // simplify the manual balances object so that we can easily reduce it
  manualBalanceByLocation: (
    state: BalanceState,
    { exchangeRate },
    { session }
  ): LocationBalance[] => {
    const mainCurrency = session?.generalSettings.mainCurrency.tickerSymbol;

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
        convertedValue =
          perLocationBalance.usdValue.multipliedBy(currentExchangeRate);
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
    const aggregateManualBalancesByLocation: BalanceByLocation =
      simplifyManualBalances.reduce(
        (result: BalanceByLocation, manualBalance: LocationBalance) => {
          if (result[manualBalance.location]) {
            // if the location exists on the reduced object, add the usdValue of the current item to the previous total
            result[manualBalance.location] = result[
              manualBalance.location
            ].plus(manualBalance.usdValue);
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
    const polkadotBalances: BlockchainAccountWithBalance[] =
      getters.polkadotBalances;
    const avaxAccounts: BlockchainAccountWithBalance[] = getters.avaxAccounts;
    const eth2Balances: BlockchainAccountWithBalance[] = getters.eth2Balances;
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
        chain: Blockchain.ETH,
        l2: l2Totals.sort((a, b) => b.usdValue.minus(a.usdValue).toNumber()),
        usdValue: sum(ethAccounts),
        loading: ethStatus === Status.NONE || ethStatus === Status.LOADING
      });
    }

    if (btcAccounts.length > 0) {
      const btcStatus = status(Section.BLOCKCHAIN_BTC);
      totals.push({
        chain: Blockchain.BTC,
        l2: [],
        usdValue: sum(btcAccounts),
        loading: btcStatus === Status.NONE || btcStatus === Status.LOADING
      });
    }

    if (kusamaBalances.length > 0) {
      const ksmStatus = status(Section.BLOCKCHAIN_KSM);
      totals.push({
        chain: Blockchain.KSM,
        l2: [],
        usdValue: sum(kusamaBalances),
        loading: ksmStatus === Status.NONE || ksmStatus === Status.LOADING
      });
    }

    if (avaxAccounts.length > 0) {
      const avaxStatus = status(Section.BLOCKCHAIN_AVAX);
      totals.push({
        chain: Blockchain.AVAX,
        l2: [],
        usdValue: sum(avaxAccounts),
        loading: avaxStatus === Status.NONE || avaxStatus === Status.LOADING
      });
    }

    if (polkadotBalances.length > 0) {
      const dotStatus = status(Section.BLOCKCHAIN_DOT);
      totals.push({
        chain: Blockchain.DOT,
        l2: [],
        usdValue: sum(polkadotBalances),
        loading: dotStatus === Status.NONE || dotStatus === Status.LOADING
      });
    }

    if (eth2Balances.length > 0) {
      const eth2Status = status(Section.BLOCKCHAIN_ETH2);
      totals.push({
        chain: Blockchain.ETH2,
        l2: [],
        usdValue: sum(eth2Balances),
        loading: eth2Status === Status.NONE || eth2Status === Status.LOADING
      });
    }

    return totals.sort((a, b) => b.usdValue.minus(a.usdValue).toNumber());
  },

  accountAssets:
    (state: BalanceState, _, { session }) =>
    (account: string) => {
      const ignoredAssets = session!.ignoredAssets;
      const ethAccount = state.eth[account];
      if (!ethAccount || isEmpty(ethAccount)) {
        return [];
      }

      return Object.entries(ethAccount.assets)
        .filter(([asset]) => !ignoredAssets.includes(asset))
        .map(
          ([key, { amount, usdValue }]) =>
            ({
              asset: key,
              amount: amount,
              usdValue: usdValue
            } as AssetBalance)
        );
    },

  accountLiabilities:
    (state: BalanceState, _, { session }) =>
    (account: string) => {
      const ignoredAssets = session!.ignoredAssets;
      const ethAccount = state.eth[account];
      if (!ethAccount || isEmpty(ethAccount)) {
        return [];
      }

      return Object.entries(ethAccount.liabilities)
        .filter(([asset]) => !ignoredAssets.includes(asset))
        .map(
          ([key, { amount, usdValue }]) =>
            ({
              asset: key,
              amount: amount,
              usdValue: usdValue
            } as AssetBalance)
        );
    },

  hasDetails: (state: BalanceState) => (account: string) => {
    const ethAccount = state.eth[account];
    const loopringBalance = state.loopringBalances[account] || {};
    if (!ethAccount || isEmpty(ethAccount)) {
      return false;
    }

    const assetsCount = Object.entries(ethAccount.assets).length;
    const liabilitiesCount = Object.entries(ethAccount.liabilities).length;
    const loopringsCount = Object.entries(loopringBalance).length;

    return assetsCount + liabilitiesCount + loopringsCount > 1;
  },

  manualLabels: ({ manualBalances, manualLiabilities }: BalanceState) => {
    const balances = manualLiabilities.concat(manualBalances);
    return balances.map(value => value.label);
  },

  assetInfo: (asset: BalanceState) => (identifier: string) => {
    if (identifier.startsWith('_nft_')) {
      for (const address in asset.nonFungibleBalances) {
        const nfb = asset.nonFungibleBalances[address];
        for (const balance of nfb) {
          if (balance.id === identifier) {
            return {
              identifier: balance.id,
              symbol: balance.name,
              name: balance.name,
              assetType: 'ethereum_token'
            } as SupportedAsset;
          }
        }
      }
    }
    return asset.supportedAssets.find(asset => asset.identifier === identifier);
  },

  accounts: (
    _,
    { ethAccounts, btcAccounts, kusamaBalances, polkadotBalances, avaxAccounts }
  ): GeneralAccount[] => {
    return ethAccounts
      .concat(btcAccounts)
      .concat(kusamaBalances)
      .concat(polkadotBalances)
      .concat(avaxAccounts)
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

  isEthereumToken:
    ({ supportedAssets }) =>
    (asset: string) => {
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
  breakdown:
    ({
      btc: { standalone, xpubs },
      btcAccounts,
      ksmAccounts,
      dotAccounts,
      avaxAccounts,
      eth,
      ethAccounts,
      exchangeBalances,
      ksm,
      dot,
      avax,
      manualBalances,
      loopringBalances
    }) =>
    asset => {
      const breakdown: AssetBreakdown[] = [];

      for (const exchange in exchangeBalances) {
        const exchangeData = exchangeBalances[exchange];
        if (!exchangeData[asset]) {
          continue;
        }

        breakdown.push({
          address: '',
          location: exchange,
          balance: exchangeData[asset],
          tags: []
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
          },
          tags: manualBalance.tags
        });
      }

      for (const address in eth) {
        const ethBalances = eth[address];
        const assetBalance = ethBalances.assets[asset];
        if (!assetBalance) {
          continue;
        }

        const tags =
          ethAccounts.find(ethAccount => ethAccount.address === address)
            ?.tags || [];

        breakdown.push({
          address,
          location: Blockchain.ETH,
          balance: assetBalance,
          tags
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
            location: Blockchain.ETH,
            balance: loopringBalances[address][asset],
            tags: [ReadOnlyTag.LOOPRING]
          });
        }
      }

      if (asset === Blockchain.BTC) {
        if (standalone) {
          for (const address in standalone) {
            const btcBalance = standalone[address];
            const tags =
              btcAccounts?.standalone.find(
                btcAccount => btcAccount.address === address
              )?.tags || [];

            breakdown.push({
              address,
              location: Blockchain.BTC,
              balance: btcBalance,
              tags
            });
          }
        }

        if (xpubs) {
          for (let i = 0; i < xpubs.length; i++) {
            const xpub = xpubs[i];
            const addresses = xpub.addresses;
            const tags = btcAccounts?.xpubs[i].tags;
            for (const address in addresses) {
              const btcBalance = addresses[address];

              breakdown.push({
                address,
                location: Blockchain.BTC,
                balance: btcBalance,
                tags
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
        const tags =
          ksmAccounts.find(ksmAccount => ksmAccount.address === address)
            ?.tags || [];

        breakdown.push({
          address,
          location: Blockchain.KSM,
          balance: assetBalance,
          tags
        });
      }

      for (const address in dot) {
        const balances = dot[address];
        const assetBalance = balances.assets[asset];
        if (!assetBalance) {
          continue;
        }

        const tags =
          dotAccounts.find(dotAccount => dotAccount.address === address)
            ?.tags || [];

        breakdown.push({
          address,
          location: Blockchain.DOT,
          balance: assetBalance,
          tags
        });
      }

      for (const address in avax) {
        const balances = avax[address];
        const assetBalance = balances.assets[asset];
        if (!assetBalance) {
          continue;
        }

        const tags =
          avaxAccounts.find(avaxAccount => avaxAccount.address === address)
            ?.tags || [];

        breakdown.push({
          address,
          location: Blockchain.AVAX,
          balance: assetBalance,
          tags
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
    const noPrice = new BigNumber(-1);
    const blockchainTotal = [
      ...totals.map(value => ({
        ...value,
        usdPrice: state.prices[value.asset] ?? noPrice
      }))
    ];
    const ignoredAssets = session!.ignoredAssets;
    const loopringBalances = state.loopringBalances;
    for (const address in loopringBalances) {
      const accountBalances = loopringBalances[address];
      for (const asset in accountBalances) {
        if (ignoredAssets.includes(asset)) {
          continue;
        }
        const existing: Writeable<AssetBalance> | undefined =
          blockchainTotal.find(value => value.asset === asset);
        if (!existing) {
          blockchainTotal.push({
            asset,
            ...accountBalances[asset],
            usdPrice: state.prices[asset] ?? noPrice
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
  assetSymbol:
    (_bs, { assetInfo }) =>
    identifier => {
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
  exchangeNonce:
    ({ connectedExchanges: exchanges }) =>
    exchange => {
      return (
        exchanges.filter(({ location }) => location === exchange).length + 1
      );
    },
  nfTotalValue: ({ nonFungibleBalances }) => {
    let sum = Zero;
    for (const address in nonFungibleBalances) {
      const addressNfts = nonFungibleBalances[address];
      for (const nft of addressNfts) {
        sum = sum.plus(nft.usdPrice);
      }
    }
    return sum;
  },
  nfBalances: ({ nonFungibleBalances }) => {
    const nfBalances: NonFungibleBalance[] = [];
    for (const address in nonFungibleBalances) {
      const addressNfBalance = nonFungibleBalances[address];
      nfBalances.push(...addressNfBalance);
    }
    return nfBalances;
  }
};
