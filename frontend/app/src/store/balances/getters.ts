import { default as BigNumber } from 'bignumber.js';
import isEmpty from 'lodash/isEmpty';
import map from 'lodash/map';
import { GetterTree } from 'vuex';
import {
  AccountBalance,
  AssetBalance,
  Balance,
  EthBalance,
  ManualBalancesByLocation,
  ManualBalanceByLocation
} from '@/model/blockchain-balances';
import { BalanceState } from '@/store/balances/state';
import {
  MakerDAOVaultModel,
  MakerDAOVaultSummary
} from '@/store/balances/types';
import { RotkehlchenState } from '@/store/store';
import { AccountDSRMovement, Blockchain, DSRBalance } from '@/typing/types';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { assetSum } from '@/utils/calculation';

export const getters: GetterTree<BalanceState, RotkehlchenState> = {
  ethAccounts(state: BalanceState): AccountBalance[] {
    return map(state.eth, (value: EthBalance, account: string) => {
      const accountBalance: AccountBalance = {
        account,
        amount: value.assets.ETH.amount,
        usdValue: value.totalUsdValue
      };
      return accountBalance;
    });
  },

  btcAccounts(state: BalanceState): AccountBalance[] {
    return map(state.btc, (value: Balance, account: string) => {
      const accountBalance: AccountBalance = {
        account,
        ...value
      };
      return accountBalance;
    });
  },

  totals(state: BalanceState): AssetBalance[] {
    return map(state.totals, (value: Balance, asset: string) => {
      const assetBalance: AssetBalance = {
        asset,
        ...value
      };
      return assetBalance;
    });
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

  exchangeBalances: (state: BalanceState) => (
    exchange: string
  ): AssetBalance[] => {
    const exchangeBalances = state.exchangeBalances[exchange];
    return exchangeBalances
      ? Object.keys(exchangeBalances).map(
          asset =>
            ({
              asset,
              amount: exchangeBalances[asset].amount,
              usdValue: exchangeBalances[asset].usdValue
            } as AssetBalance)
        )
      : [];
  },

  aggregatedBalances: (state: BalanceState, getters): AssetBalance[] => {
    const ownedAssets: { [asset: string]: AssetBalance } = {};
    const addToOwned = (value: AssetBalance) => {
      const asset = ownedAssets[value.asset];
      ownedAssets[value.asset] = !asset
        ? value
        : {
            asset: asset.asset,
            amount: asset.amount.plus(value.amount),
            usdValue: asset.usdValue.plus(value.usdValue)
          };
    };

    state.fiatBalances.forEach(value => {
      ownedAssets[value.currency] = {
        asset: value.currency,
        usdValue: value.usdValue,
        amount: value.amount
      };
    });

    for (const exchange of state.connectedExchanges) {
      const balances = getters.exchangeBalances(exchange);
      balances.forEach((value: AssetBalance) => addToOwned(value));
    }

    getters.totals.forEach((value: AssetBalance) => addToOwned(value));
    state.manualBalances.forEach(value => addToOwned(value));
    return Object.values(ownedAssets);
  },

  fiatTotal: (state: BalanceState) => {
    return state.fiatBalances.reduce((sum, balance) => {
      return sum.plus(balance.usdValue);
    }, Zero);
  },

  // simplify the manual balances object so that we can easily reduce it
  manualBalanceByLocation: (
    state: BalanceState,
    { fiatTotal, exchangeRate },
    { session }
  ) => {
    const overallFiatTotal = fiatTotal;
    const mainCurrency = session?.settings.selectedCurrency.ticker_symbol;

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
      let { location, usdValue }: ManualBalancesByLocation = {
        location: perLocationBalance.location,
        usdValue: convertedValue
      };
      return { location, usdValue };
    });

    // Aggregate all balances per location
    let aggregateManualBalancesByLocation: ManualBalanceByLocation = simplifyManualBalances.reduce(
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

    // Add fiat total to the banks aggregate
    if (aggregateManualBalancesByLocation.banks) {
      aggregateManualBalancesByLocation.banks = aggregateManualBalancesByLocation.banks.plus(
        overallFiatTotal.multipliedBy(bigNumberify(currentExchangeRate))
      );
    } else {
      if (overallFiatTotal !== Zero)
        aggregateManualBalancesByLocation.banks = fiatTotal.multipliedBy(
          bigNumberify(currentExchangeRate)
        );
    }

    return aggregateManualBalancesByLocation;
  },

  blockchainTotal: (_, getters) => {
    return getters.totals.reduce((sum: BigNumber, asset: AssetBalance) => {
      return sum.plus(asset.usdValue);
    }, Zero);
  },

  accountAssets: (state: BalanceState) => (account: string) => {
    const ethAccount = state.eth[account];
    if (!ethAccount || isEmpty(ethAccount)) {
      return [];
    }

    return Object.entries(ethAccount.assets).map(
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

  accountTags: (state: BalanceState) => (
    blockchain: Blockchain,
    address: string
  ): string[] => {
    const data = blockchain === 'ETH' ? state.ethAccounts : state.btcAccounts;
    return data[address]?.tags ?? [];
  },

  accountLabel: (state: BalanceState) => (
    blockchain: Blockchain,
    address: string
  ): string => {
    const data = blockchain === 'ETH' ? state.ethAccounts : state.btcAccounts;
    return data[address]?.label ?? '';
  },

  dsrBalances: ({ dsrBalances }: BalanceState): DSRBalance[] => {
    const { balances } = dsrBalances;
    return Object.keys(balances).map(address => ({
      address,
      balance: balances[address]
    }));
  },

  currentDSR: ({ dsrBalances }: BalanceState): BigNumber => {
    return dsrBalances.currentDSR;
  },

  totalGain: ({ dsrHistory }: BalanceState): BigNumber => {
    return Object.keys(dsrHistory)
      .map(account => dsrHistory[account])
      .reduce((sum, account) => sum.plus(account.gainSoFar), Zero);
  },

  accountGain: ({ dsrHistory }: BalanceState) => (
    account: string
  ): BigNumber => {
    return dsrHistory[account]?.gainSoFar ?? Zero;
  },

  dsrHistory: ({ dsrHistory }: BalanceState): AccountDSRMovement[] => {
    return Object.keys(dsrHistory).reduce((acc, address) => {
      const { movements } = dsrHistory[address];
      acc.push(
        ...movements.map(movement => ({
          address,
          ...movement
        }))
      );
      return acc;
    }, new Array<AccountDSRMovement>());
  },

  manualLabels: ({ manualBalances }: BalanceState) => {
    return manualBalances.map(value => value.label);
  },

  assetInfo: ({ supportedAssets }: BalanceState) => (key: string) => {
    return supportedAssets.find(asset => asset.key === key);
  },

  makerDAOVaults: ({
    makerDAOVaults,
    makerDAOVaultDetails
  }: BalanceState): MakerDAOVaultModel[] => {
    const vaults: MakerDAOVaultModel[] = [];
    for (let i = 0; i < makerDAOVaults.length; i++) {
      const vault = makerDAOVaults[i];
      const details = makerDAOVaultDetails.find(
        details => details.identifier === vault.identifier
      );
      vaults.push(details ? { ...vault, ...details } : vault);
    }
    return vaults;
  },

  makerDAOVaultSummary: ({
    makerDAOVaults
  }: BalanceState): MakerDAOVaultSummary => {
    const totalCollateralUsd = makerDAOVaults
      .map(vault => vault.collateralUsdValue)
      .reduce((sum, collateralUsdValue) => sum.plus(collateralUsdValue), Zero);
    const totalDebt = makerDAOVaults
      .map(vault => vault.debtValue)
      .reduce((sum, debt) => sum.plus(debt), Zero);
    return { totalCollateralUsd, totalDebt };
  }
};
