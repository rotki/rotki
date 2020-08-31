import { default as BigNumber } from 'bignumber.js';
import sortBy from 'lodash/sortBy';
import { GetterTree } from 'vuex';
import { truncateAddress } from '@/filters';
import { SupportedDefiProtocols } from '@/services/defi/types';
import { Status } from '@/store/const';
import {
  AaveLoan,
  DefiBalance,
  DefiLendingHistory,
  DefiLoan,
  DefiProtocolSummary,
  DefiState,
  LoanSummary,
  MakerDAOVaultModel
} from '@/store/defi/types';
import { RotkehlchenState } from '@/store/types';
import { Writeable } from '@/types';
import { DefiAccount } from '@/typing/types';
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
  loan: (identifier: string) => MakerDAOVaultModel | AaveLoan | null;
  defiAccounts: (protocols: SupportedDefiProtocols[]) => DefiAccount[];
  loans: (protocols: SupportedDefiProtocols[]) => DefiLoan[];
  loanSummary: (protocol: SupportedDefiProtocols[]) => LoanSummary;
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
  defiOverview: DefiProtocolSummary[];
}

type GettersDefinition = {
  [P in keyof DefiGetters]: (
    state: DefiState,
    getters: DefiGetters
  ) => DefiGetters[P];
};

export const getters: GetterTree<DefiState, RotkehlchenState> &
  GettersDefinition = {
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
  }: DefiState) => (protocols: SupportedDefiProtocols[]): DefiAccount[] => {
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

    const accounts: DefiAccount[] = [];
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

  loans: ({ aaveBalances, makerDAOVaults }: DefiState) => (
    protocols: SupportedDefiProtocols[]
  ): DefiLoan[] => {
    const loans: DefiLoan[] = [];
    const showAll = protocols.length === 0;

    if (showAll || protocols.includes('makerdao')) {
      loans.push(
        ...makerDAOVaults.map(
          value =>
            ({
              identifier: `${value.identifier}`,
              protocol: 'makerdao'
            } as DefiLoan)
        )
      );
    }

    if (showAll || protocols.includes('aave')) {
      for (const address of Object.keys(aaveBalances)) {
        const { borrowing } = aaveBalances[address];
        const assets = Object.keys(borrowing);
        if (assets.length === 0) {
          continue;
        }

        for (const asset of assets) {
          loans.push({
            identifier: `${asset} - ${truncateAddress(address, 6)}`,
            protocol: 'aave',
            owner: address,
            asset
          });
        }
      }
    }

    return sortBy(loans, 'identifier');
  },

  loan: (
    { makerDAOVaults, makerDAOVaultDetails, aaveBalances }: DefiState,
    { loans }
  ) => (identifier?: string): MakerDAOVaultModel | AaveLoan | null => {
    const id = identifier?.toLocaleLowerCase();
    const loan = loans([]).find(
      loan => loan.identifier.toLocaleLowerCase() === id
    );

    if (!loan) {
      return null;
    }

    if (loan.protocol === 'makerdao') {
      const vault = makerDAOVaults.find(
        vault => vault.identifier.toString().toLocaleLowerCase() === id
      );

      if (!vault) {
        return null;
      }

      const details = makerDAOVaultDetails.find(
        details => details.identifier.toString().toLocaleLowerCase() === id
      );

      return details ? { ...vault, ...details, asset: 'DAI' } : vault;
    }

    if (loan.protocol === 'aave') {
      const owner = loan.owner ?? '';
      const asset = loan.asset ?? '';
      const { borrowing, lending } = aaveBalances[owner];
      const selectedLoan = borrowing[asset];
      const collateralUsd = Object.values(lending)
        .map(({ balance }) => balance.usdValue)
        .reduce((sum, usdValue) => sum.plus(usdValue), Zero);

      return {
        asset,
        owner,
        protocol: loan.protocol,
        identifier: loan.identifier,
        stableApr: selectedLoan.stableApr,
        variableApr: selectedLoan.variableApr,
        debt: {
          amount: selectedLoan.balance.amount,
          usdValue: selectedLoan.balance.usdValue
        },
        collateral: {
          asset: '',
          amount: Zero,
          usdValue: collateralUsd
        }
      } as AaveLoan;
    }
    return null;
  },

  loanSummary: ({ makerDAOVaults, aaveBalances }: DefiState) => (
    protocols: SupportedDefiProtocols[]
  ): LoanSummary => {
    let totalCollateralUsd = Zero;
    let totalDebt = Zero;

    const showAll = protocols.length === 0;
    if (showAll || protocols.includes('makerdao')) {
      totalCollateralUsd = makerDAOVaults
        .map(({ collateral: { usdValue } }) => usdValue)
        .reduce((sum, collateralUsdValue) => sum.plus(collateralUsdValue), Zero)
        .plus(totalCollateralUsd);

      totalDebt = makerDAOVaults
        .map(({ debt: { usdValue } }) => usdValue)
        .reduce((sum, debt) => sum.plus(debt), Zero)
        .plus(totalDebt);
    }

    if (showAll || protocols.includes('aave')) {
      for (const address of Object.keys(aaveBalances)) {
        const { borrowing, lending } = aaveBalances[address];
        totalCollateralUsd = Object.values(lending)
          .map(({ balance: { usdValue } }) => usdValue)
          .reduce(
            (sum, collateralUsdValue) => sum.plus(collateralUsdValue),
            Zero
          )
          .plus(totalCollateralUsd);

        totalDebt = Object.values(borrowing)
          .map(({ balance: { usdValue } }) => usdValue)
          .reduce(
            (sum, collateralUsdValue) => sum.plus(collateralUsdValue),
            Zero
          )
          .plus(totalDebt);
      }
    }

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
  },

  defiOverview: (
    { allProtocols, status },
    { loanSummary, totalLendingDeposit }
  ) => {
    const summary: { [protocol: string]: Writeable<DefiProtocolSummary> } = {};

    for (const address of Object.keys(allProtocols)) {
      const protocols = allProtocols[address];
      for (let i = 0; i < protocols.length; i++) {
        const entry = protocols[i];
        const protocol = entry.protocol.name;

        if (protocol === 'Aave') {
          if (status !== Status.LOADED && status !== Status.REFRESHING) {
            continue;
          }
          const filter: SupportedDefiProtocols[] = ['aave'];
          const { totalCollateralUsd, totalDebt } = loanSummary(filter);
          summary[protocol] = {
            protocol: {
              name: protocol,
              icon: entry.protocol.icon
            },
            assets: [],
            borrowingUrl: '/defi/borrowing?protocol=aave',
            lendingUrl: '/defi/lending?protocol=aave',
            totalCollateralUsd,
            totalDebtUsd: totalDebt,
            totalLendingDepositUsd: totalLendingDeposit(filter, [])
          };
          continue;
        }

        if (!summary[protocol]) {
          summary[protocol] = {
            protocol: { ...entry.protocol },
            tokenInfo: {
              tokenName: entry.baseBalance.tokenName,
              tokenSymbol: entry.baseBalance.tokenSymbol
            },
            assets: [],
            totalCollateralUsd: Zero,
            totalDebtUsd: Zero,
            totalLendingDepositUsd: Zero
          };
        }

        const { balance } = entry.baseBalance;
        if (entry.balanceType === 'Asset') {
          const previousBalance = summary[protocol].balanceUsd ?? Zero;
          summary[protocol].balanceUsd = previousBalance.plus(balance.usdValue);
          summary[protocol].assets.push(entry.baseBalance);
        }
      }
    }

    if (status === Status.LOADED || status === Status.REFRESHING) {
      const filter: SupportedDefiProtocols[] = ['makerdao'];
      const { totalCollateralUsd, totalDebt } = loanSummary(filter);
      summary['makerdao'] = {
        protocol: {
          name: 'MakerDAO',
          icon: ''
        },
        assets: [],
        borrowingUrl: '/defi/borrowing?protocol=makerdao',
        lendingUrl: '/defi/lending?protocol=makerdao',
        totalCollateralUsd,
        totalDebtUsd: totalDebt,
        totalLendingDepositUsd: totalLendingDeposit(filter, [])
      };
    }

    return sortBy(Object.values(summary), 'protocol.name');
  }
};
