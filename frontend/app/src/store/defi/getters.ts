import { default as BigNumber } from 'bignumber.js';
import sortBy from 'lodash/sortBy';
import { SupportedDefiProtocols } from '@/services/defi/types';
import {
  DefiBalance,
  DefiLendingHistory,
  DefiState,
  MakerDAOVaultModel,
  MakerDAOVaultSummary
} from '@/store/defi/types';
import { Account } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

const unique = function (
  value: string,
  index: number,
  array: string[]
): boolean {
  return array.indexOf(value) === index;
};

export interface DefiGetters {
  totalUsdEarned: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BigNumber;
  totalLendingDeposit: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BigNumber;
  makerDAOVaults: MakerDAOVaultModel[];
  makerDAOVaultSummary: MakerDAOVaultSummary;
  defiAccounts: (protocols: SupportedDefiProtocols[]) => Account[];
  effectiveInterestRate: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => string;
  lendingBalances: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => DefiBalance[];
  lendingHistory: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => DefiLendingHistory<SupportedDefiProtocols>[];
}

type GettersDefinition = {
  [P in keyof DefiGetters]: (
    state: DefiState,
    getters: DefiGetters
  ) => DefiGetters[P];
};

export const getters: GettersDefinition = {
  totalUsdEarned: ({ dsrHistory, aaveHistory }: DefiState) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): BigNumber => {
    let total = Zero;
    const showAll = protocols.length === 0;
    const allAddresses = addresses.length === 0;

    if (showAll || protocols.includes('makerdao')) {
      for (const address of Object.keys(dsrHistory)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        total = total.plus(dsrHistory[address].gainSoFarUsdValue);
      }
    }

    if (showAll || protocols.includes('aave')) {
      for (const address of Object.keys(aaveHistory)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const totalEarned = aaveHistory[address].totalEarned;
        for (const asset of Object.keys(totalEarned)) {
          total = total.plus(totalEarned[asset].usdValue);
        }
      }
    }
    return total;
  },

  defiAccounts: ({
    aaveBalances,
    aaveHistory,
    dsrBalances,
    dsrHistory
  }: DefiState) => (protocols: SupportedDefiProtocols[]): Account[] => {
    const aaveAddresses: string[] = [];
    const makerAddresses: string[] = [];
    if (protocols.length === 0 || protocols.includes('aave')) {
      const uniqueAddresses: string[] = [
        ...Object.keys(aaveBalances),
        ...Object.keys(aaveHistory)
      ].filter(unique);
      aaveAddresses.push(...uniqueAddresses);
    }

    if (protocols.length === 0 || protocols.includes('makerdao')) {
      const uniqueAddresses: string[] = [
        ...Object.keys(dsrHistory),
        ...Object.keys(dsrBalances.balances)
      ].filter(unique);
      makerAddresses.push(...uniqueAddresses);
    }

    const accounts: Account[] = [];
    for (const address of aaveAddresses) {
      const protocols: SupportedDefiProtocols[] = ['aave'];
      const index = makerAddresses.indexOf(address);
      if (index >= 0) {
        protocols.push('makerdao');
        makerAddresses.splice(index, 1);
      }
      accounts.push({
        address,
        chain: 'ETH',
        protocols
      });
    }

    for (const address of makerAddresses) {
      accounts.push({
        address,
        chain: 'ETH',
        protocols: ['makerdao']
      });
    }

    return accounts;
  },

  makerDAOVaults: ({
    makerDAOVaults,
    makerDAOVaultDetails
  }: DefiState): MakerDAOVaultModel[] => {
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
  }: DefiState): MakerDAOVaultSummary => {
    const totalCollateralUsd = makerDAOVaults
      .map(vault => vault.collateralUsdValue)
      .reduce((sum, collateralUsdValue) => sum.plus(collateralUsdValue), Zero);
    const totalDebt = makerDAOVaults
      .map(vault => vault.debtValue)
      .reduce((sum, debt) => sum.plus(debt), Zero);
    return { totalCollateralUsd, totalDebt };
  },

  effectiveInterestRate: (_, { lendingBalances }) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): string => {
    const { usdValue: value, weight } = lendingBalances(protocols, addresses)
      .map(({ effectiveInterestRate, balance: { usdValue } }) => {
        return {
          weight: usdValue.multipliedBy(parseFloat(effectiveInterestRate)),
          usdValue
        };
      })
      .reduce(
        (sum, current) => ({
          weight: sum.weight.plus(current.weight),
          usdValue: sum.usdValue.plus(current.usdValue)
        }),
        {
          weight: Zero,
          usdValue: Zero
        }
      );

    const effectiveInterestRate = weight.div(value);
    return effectiveInterestRate.isNaN()
      ? '0.00%'
      : `${effectiveInterestRate.toFormat(2)}%`;
  },

  totalLendingDeposit: (_: DefiState, { lendingBalances }) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): BigNumber => {
    return lendingBalances(protocols, addresses)
      .map(value => value.balance.usdValue)
      .reduce((sum, usdValue) => sum.plus(usdValue), Zero);
  },

  lendingBalances: ({ dsrBalances, aaveBalances }: DefiState) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): DefiBalance[] => {
    const balances: DefiBalance[] = [];
    const showAll = protocols.length === 0;
    const allAddresses = addresses.length === 0;

    if (showAll || protocols.includes('makerdao')) {
      for (const address of Object.keys(dsrBalances.balances)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const balance = dsrBalances.balances[address];
        balances.push({
          address,
          protocol: 'makerdao',
          asset: 'DAI',
          balance: { ...balance },
          effectiveInterestRate: `${dsrBalances.currentDSR.toFormat(2)}%`
        });
      }
    }

    if (showAll || protocols.includes('aave')) {
      for (const address of Object.keys(aaveBalances)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const { lending } = aaveBalances[address];

        for (const asset of Object.keys(lending)) {
          const aaveAsset = lending[asset];
          balances.push({
            address,
            protocol: 'aave',
            asset,
            effectiveInterestRate: aaveAsset.apy,
            balance: { ...aaveAsset.balance }
          });
        }
      }
    }
    return sortBy(balances, 'asset');
  },

  lendingHistory: ({ dsrHistory, aaveHistory }: DefiState) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): DefiLendingHistory<SupportedDefiProtocols>[] => {
    const defiLendingHistory: DefiLendingHistory<SupportedDefiProtocols>[] = [];
    const showAll = protocols.length === 0;
    const allAddresses = addresses.length === 0;
    let id = 1;

    if (showAll || protocols.includes('makerdao')) {
      for (const address of Object.keys(dsrHistory)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }

        const history = dsrHistory[address];

        for (const movement of history.movements) {
          defiLendingHistory.push({
            id: id++,
            eventType: movement.movementType,
            protocol: 'makerdao',
            address,
            asset: 'DAI',
            value: movement.balance,
            blockNumber: movement.blockNumber,
            timestamp: movement.timestamp,
            txHash: movement.txHash,
            extras: {
              gainSoFar: movement.gainSoFar
            }
          });
        }
      }
    }

    if (showAll || protocols.includes('aave')) {
      for (const address of Object.keys(aaveHistory)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }

        const history = aaveHistory[address];

        for (const event of history.events) {
          const items = {
            id: id++,
            eventType: event.eventType,
            protocol: 'aave',
            address,
            asset: event.asset,
            value: event.value,
            blockNumber: event.blockNumber,
            timestamp: event.timestamp,
            txHash: event.txHash,
            extras: {}
          } as DefiLendingHistory<'aave'>;
          defiLendingHistory.push(items);
        }
      }
    }
    return sortBy(defiLendingHistory, 'timestamp').reverse();
  }
};
