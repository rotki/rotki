import { default as BigNumber } from 'bignumber.js';
import sortBy from 'lodash/sortBy';
import { GetterTree } from 'vuex';
import { truncateAddress } from '@/filters';
import {
  DEFI_AAVE,
  DEFI_COMPOUND,
  DEFI_MAKERDAO,
  DEFI_YEARN_VAULTS
} from '@/services/defi/consts';
import { SupportedDefiProtocols } from '@/services/defi/types';
import { CompoundLoan } from '@/services/defi/types/compound';
import { DEPOSIT } from '@/services/defi/types/consts';
import {
  SupportedYearnVault,
  YearnVaultProfitLoss
} from '@/services/defi/types/yearn';
import { Balance } from '@/services/types-api';
import { Section, Status } from '@/store/const';
import {
  AaveLoan,
  BaseDefiBalance,
  Collateral,
  CompoundProfitLossModel,
  DefiBalance,
  DefiLendingHistory,
  DefiLoan,
  DefiProtocolSummary,
  DefiState,
  LoanSummary,
  MakerDAOVaultModel
} from '@/store/defi/types';
import { balanceUsdValueSum, toProfitLossModel } from '@/store/defi/utils';
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
  loan: (
    identifier: string
  ) => MakerDAOVaultModel | AaveLoan | CompoundLoan | null;
  defiAccounts: (protocols: SupportedDefiProtocols[]) => DefiAccount[];
  loans: (protocols: SupportedDefiProtocols[]) => DefiLoan[];
  loanSummary: (protocol: SupportedDefiProtocols[]) => LoanSummary;
  effectiveInterestRate: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => string;
  aggregatedLendingBalances: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BaseDefiBalance[];
  lendingBalances: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => DefiBalance[];
  lendingHistory: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => DefiLendingHistory<SupportedDefiProtocols>[];
  defiOverview: DefiProtocolSummary[];
  compoundRewards: CompoundProfitLossModel[];
  compoundInterestProfit: CompoundProfitLossModel[];
  compoundDebtLoss: CompoundProfitLossModel[];
  yearnVaultsProfit: (addresses: string[]) => YearnVaultProfitLoss[];
}

type GettersDefinition = {
  [P in keyof DefiGetters]: (
    state: DefiState,
    getters: DefiGetters,
    rootState: RotkehlchenState,
    rootGetters: any
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
        total = total.plus(dsrHistory[address].gainSoFar.usdValue);
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

  loans: ({
    aaveBalances,
    makerDAOVaults,
    compoundBalances,
    compoundHistory: { events }
  }: DefiState) => (protocols: SupportedDefiProtocols[]): DefiLoan[] => {
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

    if (showAll || protocols.includes('compound')) {
      const assetAddressPair = events
        .filter(
          ({ eventType }) => !['mint', 'redeem', 'comp'].includes(eventType)
        )
        .map(({ asset, address }) => ({ asset, address }));

      for (const address of Object.keys(compoundBalances)) {
        const { borrowing } = compoundBalances[address];
        const assets = Object.keys(borrowing);

        if (assets.length === 0) {
          continue;
        }

        for (const asset of assets) {
          assetAddressPair.push({ asset, address });
        }
      }
      assetAddressPair
        .filter(
          (value, index, array) =>
            array.findIndex(
              ({ address, asset }) =>
                value.asset === asset && value.address === address
            ) === index
        )
        .forEach(({ address, asset }) => {
          loans.push({
            identifier: `${asset} - ${truncateAddress(address, 6)}`,
            protocol: 'compound',
            owner: address,
            asset
          });
        });
    }

    return sortBy(loans, 'identifier');
  },

  loan: (
    {
      makerDAOVaults,
      makerDAOVaultDetails,
      aaveBalances,
      compoundBalances,
      compoundHistory: { events }
    }: DefiState,
    { loans }
  ) => (
    identifier?: string
  ): MakerDAOVaultModel | AaveLoan | CompoundLoan | null => {
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
        collateral: Object.keys(lending).map(asset => ({
          asset,
          ...lending[asset].balance
        }))
      } as AaveLoan;
    }

    if (loan.protocol === 'compound') {
      const owner = loan.owner ?? '';
      const asset = loan.asset ?? '';

      let apy: string = '0%';
      let debt: Balance = { amount: Zero, usdValue: Zero };
      let collateral: Collateral<string>[] = [];

      if (compoundBalances[owner]) {
        const { borrowing, lending } = compoundBalances[owner];
        const selectedLoan = borrowing[asset];

        if (selectedLoan) {
          apy = selectedLoan.apy;
          debt = selectedLoan.balance;
          collateral = Object.keys(lending).map(asset => ({
            asset,
            ...lending[asset].balance
          }));
        }
      }

      return {
        asset,
        owner,
        protocol: loan.protocol,
        identifier: loan.identifier,
        apy,
        debt,
        collateral,
        events: events
          .filter(event => event.asset === asset || event.eventType === 'comp')
          .filter(({ address }) => address === owner)
          .filter(({ eventType }) => !['mint', 'redeem'].includes(eventType))
          .map(value => ({ ...value, id: `${value.txHash}${value.logIndex}` }))
      } as CompoundLoan;
    }

    return null;
  },

  loanSummary: ({
    makerDAOVaults,
    aaveBalances,
    compoundBalances
  }: DefiState) => (protocols: SupportedDefiProtocols[]): LoanSummary => {
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
        totalCollateralUsd = balanceUsdValueSum(Object.values(lending)).plus(
          totalCollateralUsd
        );

        totalDebt = balanceUsdValueSum(Object.values(borrowing)).plus(
          totalDebt
        );
      }
    }

    if (showAll || protocols.includes('compound')) {
      for (const address of Object.keys(compoundBalances)) {
        const { borrowing, lending } = compoundBalances[address];
        totalCollateralUsd = balanceUsdValueSum(Object.values(lending)).plus(
          totalCollateralUsd
        );

        totalDebt = balanceUsdValueSum(Object.values(borrowing)).plus(
          totalDebt
        );
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

  aggregatedLendingBalances: (_, { lendingBalances }) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): BaseDefiBalance[] => {
    const balances = lendingBalances(protocols, addresses).reduce(
      (grouped, { address, protocol, ...baseBalance }) => {
        const { asset } = baseBalance;
        if (!grouped[asset]) {
          grouped[asset] = [baseBalance];
        } else {
          grouped[asset].push(baseBalance);
        }

        return grouped;
      },
      {} as { [asset: string]: BaseDefiBalance[] }
    );

    const aggregated: BaseDefiBalance[] = [];

    for (const asset in balances) {
      const { weight, amount, usdValue } = balances[asset]
        .map(({ effectiveInterestRate, balance: { usdValue, amount } }) => {
          return {
            weight: usdValue.multipliedBy(parseFloat(effectiveInterestRate)),
            usdValue,
            amount
          };
        })
        .reduce(
          (sum, current) => ({
            weight: sum.weight.plus(current.weight),
            usdValue: sum.usdValue.plus(current.usdValue),
            amount: sum.amount.plus(current.amount)
          }),
          {
            weight: Zero,
            usdValue: Zero,
            amount: Zero
          }
        );

      const effectiveInterestRate = weight.div(usdValue);

      aggregated.push({
        asset,
        balance: {
          amount,
          usdValue
        },
        effectiveInterestRate: effectiveInterestRate.isNaN()
          ? '0.00%'
          : `${effectiveInterestRate.toFormat(2)}%`
      });
    }
    return aggregated;
  },

  lendingBalances: ({
    dsrBalances,
    aaveBalances,
    compoundBalances
  }: DefiState) => (
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

    if (showAll || protocols.includes('compound')) {
      for (const address of Object.keys(compoundBalances)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const { lending } = compoundBalances[address];
        for (const asset of Object.keys(lending)) {
          const assetDetails = lending[asset];
          balances.push({
            address,
            protocol: 'compound',
            asset,
            effectiveInterestRate: assetDetails.apy ?? '0%',
            balance: { ...assetDetails.balance }
          });
        }
      }
    }

    return sortBy(balances, 'asset');
  },

  lendingHistory: ({
    dsrHistory,
    aaveHistory,
    compoundHistory,
    yearnVaultsHistory
  }: DefiState) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): DefiLendingHistory<SupportedDefiProtocols>[] => {
    const defiLendingHistory: DefiLendingHistory<SupportedDefiProtocols>[] = [];
    const showAll = protocols.length === 0;
    const allAddresses = addresses.length === 0;
    let id = 1;

    if (showAll || protocols.includes(DEFI_MAKERDAO)) {
      for (const address of Object.keys(dsrHistory)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }

        const history = dsrHistory[address];

        for (const movement of history.movements) {
          defiLendingHistory.push({
            id: `${movement.txHash}${id++}`,
            eventType: movement.movementType,
            protocol: 'makerdao',
            address,
            asset: 'DAI',
            value: movement.value,
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

    if (showAll || protocols.includes(DEFI_AAVE)) {
      for (const address of Object.keys(aaveHistory)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }

        const history = aaveHistory[address];

        for (const event of history.events) {
          const items = {
            id: `${event.txHash}${event.logIndex}`,
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

    if (showAll || protocols.includes(DEFI_COMPOUND)) {
      for (const event of compoundHistory.events) {
        if (!allAddresses && !addresses.includes(event.address)) {
          continue;
        }
        if (!['mint', 'redeem', 'comp'].includes(event.eventType)) {
          continue;
        }

        const item = {
          id: `${event.txHash}${event.logIndex}`,
          eventType: event.eventType,
          protocol: 'compound',
          address: event.address,
          asset: event.asset,
          value: event.value,
          blockNumber: event.blockNumber,
          timestamp: event.timestamp,
          txHash: event.txHash,
          extras: {
            eventType: event.eventType,
            asset: event.asset,
            value: event.value,
            toAsset: event.toAsset,
            toValue: event.toValue,
            realizedPnl: event.realizedPnl
          }
        } as DefiLendingHistory<'compound'>;
        defiLendingHistory.push(item);
      }
    }

    if (showAll || protocols.includes(DEFI_YEARN_VAULTS)) {
      for (const address in yearnVaultsHistory) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const history = yearnVaultsHistory[address];

        for (const vault in history) {
          const data = history[vault as SupportedYearnVault];
          if (!data || !data.events || data.events.length === 0) {
            continue;
          }
          for (const event of data.events) {
            const item = {
              id: `${event.txHash}${event.logIndex}`,
              eventType: event.eventType,
              protocol: DEFI_YEARN_VAULTS,
              address: address,
              asset: event.fromAsset,
              value: event.fromValue,
              blockNumber: event.blockNumber,
              timestamp: event.timestamp,
              txHash: event.txHash,
              extras: {
                eventType: event.eventType,
                asset: event.fromAsset,
                value: event.fromValue,
                toAsset: event.toAsset,
                toValue: event.toValue,
                realizedPnl: event.realizedPnl
              }
            } as DefiLendingHistory<'yearn_vaults'>;
            defiLendingHistory.push(item);
          }
        }
      }
    }
    return sortBy(defiLendingHistory, 'timestamp').reverse();
  },

  defiOverview: (
    { allProtocols },
    { loanSummary, totalLendingDeposit },
    _,
    { status }
  ) => {
    const protocolSummary = (
      protocol: SupportedDefiProtocols,
      icon: string,
      section: Section
    ): DefiProtocolSummary | undefined => {
      const currentStatus = status(section);
      if (
        currentStatus !== Status.LOADED &&
        currentStatus !== Status.REFRESHING
      ) {
        return undefined;
      }
      const filter: SupportedDefiProtocols[] = [protocol];
      const { totalCollateralUsd, totalDebt } = loanSummary(filter);
      return {
        protocol: {
          name: protocol,
          icon: icon
        },
        assets: [],
        borrowingUrl: `/defi/borrowing?protocol=${protocol}`,
        lendingUrl: `/defi/lending?protocol=${protocol}`,
        totalCollateralUsd,
        totalDebtUsd: totalDebt,
        totalLendingDepositUsd: totalLendingDeposit(filter, [])
      };
    };
    const summary: { [protocol: string]: Writeable<DefiProtocolSummary> } = {};

    for (const address of Object.keys(allProtocols)) {
      const protocols = allProtocols[address];
      for (let i = 0; i < protocols.length; i++) {
        const entry = protocols[i];
        const protocol = entry.protocol.name;

        if (protocol === 'Aave') {
          const aaveSummary = protocolSummary(
            'aave',
            entry.protocol.icon,
            Section.DEFI_AAVE_BALANCES
          );

          if (aaveSummary) {
            summary[protocol] = aaveSummary;
          }
          continue;
        }

        if (protocol === 'Compound') {
          const compoundSummary = protocolSummary(
            'compound',
            entry.protocol.icon,
            Section.DEFI_COMPOUND_BALANCES
          );

          if (compoundSummary) {
            summary[protocol] = compoundSummary;
          }
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
          const assetIndex = summary[protocol].assets.findIndex(
            asset => asset.tokenAddress === entry.baseBalance.tokenAddress
          );
          if (assetIndex >= 0) {
            const { usdValue, amount } = entry.baseBalance.balance;
            const asset = summary[protocol].assets[assetIndex];
            const usdValueSum = usdValue.plus(asset.balance.usdValue);
            const amountSum = amount.plus(asset.balance.amount);

            summary[protocol].assets[assetIndex] = {
              ...asset,
              balance: {
                usdValue: usdValueSum,
                amount: amountSum
              }
            };
          } else {
            summary[protocol].assets.push(entry.baseBalance);
          }
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
  },

  compoundRewards: ({ compoundHistory }): CompoundProfitLossModel[] => {
    return toProfitLossModel(compoundHistory.rewards);
  },

  compoundInterestProfit: ({ compoundHistory }): CompoundProfitLossModel[] => {
    return toProfitLossModel(compoundHistory.interestProfit);
  },

  compoundDebtLoss: ({ compoundHistory }): CompoundProfitLossModel[] => {
    return toProfitLossModel(compoundHistory.debtLoss);
  },

  compoundLiquidationProfit: ({
    compoundHistory
  }): CompoundProfitLossModel[] => {
    return toProfitLossModel(compoundHistory.liquidationProfit);
  },

  yearnVaultsProfit: ({ yearnVaultsHistory }) => (
    addresses: string[]
  ): YearnVaultProfitLoss[] => {
    const yearnVaultsProfit: YearnVaultProfitLoss[] = [];
    const allAddresses = addresses.length === 0;
    for (const address in yearnVaultsHistory) {
      if (!allAddresses && !addresses.includes(address)) {
        continue;
      }
      const history = yearnVaultsHistory[address];
      for (const key in history) {
        const vault = key as SupportedYearnVault;
        const data = history[vault];
        if (!data) {
          continue;
        }

        const events = data.events.filter(event => event.eventType === DEPOSIT);
        const asset = events && events.length > 0 ? events[0].fromAsset : '';

        const vaultProfit: YearnVaultProfitLoss = {
          value: data.profitLoss,
          vault,
          asset
        };

        yearnVaultsProfit.push(vaultProfit);
      }
    }
    return yearnVaultsProfit;
  }
};
