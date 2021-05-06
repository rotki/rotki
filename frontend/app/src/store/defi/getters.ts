import { default as BigNumber } from 'bignumber.js';
import sortBy from 'lodash/sortBy';
import { truncateAddress } from '@/filters';
import i18n from '@/i18n';
import {
  AAVE_BORROWING_EVENTS,
  AAVE_LENDING_EVENTS,
  DEFI_AAVE,
  DEFI_COMPOUND,
  DEFI_EVENT_LIQUIDATION,
  DEFI_MAKERDAO,
  DEFI_YEARN_VAULTS
} from '@/services/defi/consts';
import { SupportedDefiProtocols, TokenDetails } from '@/services/defi/types';
import {
  AaveEvent,
  AaveHistoryEvents,
  AaveHistoryTotal,
  AaveLending
} from '@/services/defi/types/aave';
import { CompoundLoan } from '@/services/defi/types/compound';
import { DEPOSIT } from '@/services/defi/types/consts';
import {
  SupportedYearnVault,
  YearnVaultAsset,
  YearnVaultBalance,
  YearnVaultProfitLoss
} from '@/services/defi/types/yearn';
import { Trade } from '@/services/history/types';
import { Balance } from '@/services/types-api';
import { Section, Status } from '@/store/const';
import {
  AAVE,
  AIRDROP_POAP,
  COMPOUND,
  getProtcolIcon,
  GETTER_BALANCER_BALANCES,
  GETTER_UNISWAP_ASSETS,
  MAKERDAO,
  YEARN_FINANCE_VAULTS
} from '@/store/defi/const';
import {
  AaveLoan,
  Airdrop,
  AirdropDetail,
  AirdropType,
  BalancerBalanceWithOwner,
  BaseDefiBalance,
  Collateral,
  DefiBalance,
  DefiLendingHistory,
  DefiLoan,
  DefiProtocolSummary,
  DefiState,
  LoanSummary,
  MakerDAOVaultModel,
  OverviewDefiProtocol,
  PoapDelivery,
  ProfitLossModel,
  TokenInfo,
  UniswapBalance,
  UniswapEventDetails,
  UniswapPool,
  UniswapPoolProfit,
  DexTrade,
  DexTrades,
  BalancerEvent,
  Pool,
  BalancerProfitLoss
} from '@/store/defi/types';
import { balanceUsdValueSum, toProfitLossModel } from '@/store/defi/utils';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { filterAddresses } from '@/store/utils';
import { Writeable } from '@/types';
import { DefiAccount, ETH } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';

function isLendingEvent(value: AaveHistoryEvents): value is AaveEvent {
  const lending: string[] = [...AAVE_LENDING_EVENTS];
  return lending.indexOf(value.eventType) !== -1;
}

function assetIdentifier(details: TokenDetails) {
  if (typeof details === 'string') {
    return details;
  }
  return `_ceth_${details.ethereumAddress}`;
}

interface DefiGetters {
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
  compoundRewards: ProfitLossModel[];
  compoundInterestProfit: ProfitLossModel[];
  compoundLiquidationProfit: ProfitLossModel[];
  compoundDebtLoss: ProfitLossModel[];
  yearnVaultsProfit: (addresses: string[]) => YearnVaultProfitLoss[];
  yearnVaultsAssets: (addresses: string[]) => YearnVaultBalance[];
  aaveTotalEarned: (addresses: string[]) => ProfitLossModel[];
  uniswapBalances: (addresses: string[]) => UniswapBalance[];
  basicDexTrades: (addresses: string[]) => Trade[];
  uniswapPoolProfit: (addresses: string[]) => UniswapPoolProfit[];
  uniswapEvents: (addresses: string[]) => UniswapEventDetails[];
  uniswapAddresses: string[];
  dexTrades: (addresses: string[]) => DexTrade[];
  airdrops: (addresses: string[]) => Airdrop[];
  airdropAddresses: string[];
  [GETTER_UNISWAP_ASSETS]: UniswapPool[];
  [GETTER_BALANCER_BALANCES]: BalancerBalanceWithOwner[];
  balancerAddresses: string[];
  balancerEvents: (addresses: string[]) => BalancerEvent[];
  balancerPools: Pool[];
  balancerProfitLoss: (addresses: string[]) => BalancerProfitLoss[];
}

export const getters: Getters<DefiState, DefiGetters, RotkehlchenState, any> = {
  totalUsdEarned: ({
    dsrHistory,
    aaveHistory,
    compoundHistory,
    yearnVaultsHistory
  }: DefiState) => (
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

    if (showAll || protocols.includes(DEFI_AAVE)) {
      for (const address of Object.keys(aaveHistory)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const totalEarned = aaveHistory[address].totalEarnedInterest;
        for (const asset of Object.keys(totalEarned)) {
          total = total.plus(totalEarned[asset].usdValue);
        }
      }
    }

    if (showAll || protocols.includes(DEFI_COMPOUND)) {
      for (const address in compoundHistory.interestProfit) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }

        const accountProfit = compoundHistory.interestProfit[address];
        for (const asset in accountProfit) {
          const assetProfit = accountProfit[asset];
          total = total.plus(assetProfit.usdValue);
        }
      }
    }

    if (showAll || protocols.includes(DEFI_YEARN_VAULTS)) {
      for (const address in yearnVaultsHistory) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const accountVaults = yearnVaultsHistory[address];
        for (const key in accountVaults) {
          const vault = key as SupportedYearnVault;
          const vaultData = accountVaults[vault];
          if (!vaultData) {
            continue;
          }
          total = total.plus(vaultData.profitLoss.usdValue);
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
    if (protocols.length === 0 || protocols.includes(DEFI_AAVE)) {
      const uniqueAddresses: string[] = [
        ...Object.keys(aaveBalances),
        ...Object.keys(aaveHistory)
      ].filter(uniqueStrings);
      aaveAddresses.push(...uniqueAddresses);
    }

    if (protocols.length === 0 || protocols.includes(DEFI_MAKERDAO)) {
      const uniqueAddresses: string[] = [
        ...Object.keys(dsrHistory),
        ...Object.keys(dsrBalances.balances)
      ].filter(uniqueStrings);
      makerAddresses.push(...uniqueAddresses);
    }

    const accounts: DefiAccount[] = [];
    for (const address of aaveAddresses) {
      const protocols: SupportedDefiProtocols[] = [DEFI_AAVE];
      const index = makerAddresses.indexOf(address);
      if (index >= 0) {
        protocols.push(DEFI_MAKERDAO);
        makerAddresses.splice(index, 1);
      }
      accounts.push({
        address,
        chain: ETH,
        protocols
      });
    }

    for (const address of makerAddresses) {
      accounts.push({
        address,
        chain: ETH,
        protocols: [DEFI_MAKERDAO]
      });
    }

    return accounts;
  },

  loans: (
    {
      aaveBalances,
      aaveHistory,
      makerDAOVaults,
      compoundBalances,
      compoundHistory: { events }
    }: DefiState,
    _dg,
    _rs,
    { 'balances/assetInfo': assetInfo }
  ) => (protocols: SupportedDefiProtocols[]): DefiLoan[] => {
    const loans: DefiLoan[] = [];
    const showAll = protocols.length === 0;

    if (showAll || protocols.includes(DEFI_MAKERDAO)) {
      loans.push(
        ...makerDAOVaults.map(
          value =>
            ({
              identifier: `${value.identifier}`,
              protocol: DEFI_MAKERDAO
            } as DefiLoan)
        )
      );
    }

    if (showAll || protocols.includes(DEFI_AAVE)) {
      const knownAssets: string[] = [];
      for (const address of Object.keys(aaveBalances)) {
        const { borrowing } = aaveBalances[address];
        const assets = Object.keys(borrowing);
        if (assets.length === 0) {
          continue;
        }

        for (const asset of assets) {
          const symbol = assetInfo(asset)?.symbol ?? asset;
          loans.push({
            identifier: `${symbol} - ${truncateAddress(address, 6)}`,
            protocol: DEFI_AAVE,
            owner: address,
            asset
          });
          knownAssets.push(asset);
        }
      }

      for (const address in aaveHistory) {
        const { events } = aaveHistory[address];
        const borrowEvents: string[] = [...AAVE_BORROWING_EVENTS];
        const historyAssets = events
          .filter(e => borrowEvents.includes(e.eventType))
          .map(event =>
            event.eventType === DEFI_EVENT_LIQUIDATION
              ? event.principalAsset
              : event.asset
          )
          .filter(uniqueStrings)
          .filter(asset => !knownAssets.includes(asset));

        for (const asset of historyAssets) {
          const symbol = assetInfo(asset)?.symbol ?? asset;
          loans.push({
            identifier: `${symbol} - ${truncateAddress(address, 6)}`,
            protocol: DEFI_AAVE,
            owner: address,
            asset
          });
        }
      }
    }

    if (showAll || protocols.includes(DEFI_COMPOUND)) {
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
            protocol: DEFI_COMPOUND,
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
      aaveHistory,
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

    if (loan.protocol === DEFI_MAKERDAO) {
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

    if (loan.protocol === DEFI_AAVE) {
      const owner = loan.owner ?? '';
      const asset = loan.asset ?? '';

      let selectedLoan = {
        stableApr: '-',
        variableApr: '-',
        balance: { amount: Zero, usdValue: Zero }
      };
      let lending: AaveLending = {};
      if (aaveBalances[owner]) {
        const balances = aaveBalances[owner];
        selectedLoan = balances.borrowing[asset] ?? selectedLoan;
        lending = balances.lending ?? lending;
      }

      const lost: Writeable<AaveHistoryTotal> = {};
      const liquidationEarned: Writeable<AaveHistoryTotal> = {};
      const events: AaveHistoryEvents[] = [];
      if (aaveHistory[owner]) {
        const {
          totalLost,
          events: allEvents,
          totalEarnedLiquidations
        } = aaveHistory[owner];

        for (const event of allEvents) {
          if (event.eventType !== DEFI_EVENT_LIQUIDATION) {
            continue;
          }

          if (event.principalAsset !== asset) {
            continue;
          }

          const collateralAsset = event.collateralAsset;

          if (!lost[collateralAsset] && totalLost[collateralAsset]) {
            lost[collateralAsset] = totalLost[collateralAsset];
          }

          if (
            !liquidationEarned[collateralAsset] &&
            totalEarnedLiquidations[collateralAsset]
          ) {
            liquidationEarned[collateralAsset] =
              totalEarnedLiquidations[collateralAsset];
          }
        }

        if (totalLost[asset]) {
          lost[asset] = totalLost[asset];
        }
        if (!liquidationEarned[asset] && totalEarnedLiquidations[asset]) {
          liquidationEarned[asset] = totalEarnedLiquidations[asset];
        }

        events.push(
          ...allEvents.filter(event => {
            let isAsset: boolean;
            if (event.eventType !== DEFI_EVENT_LIQUIDATION) {
              isAsset = event.asset === asset;
            } else {
              isAsset = event.principalAsset === asset;
            }
            return (
              isAsset &&
              AAVE_BORROWING_EVENTS.find(
                eventType => eventType === event.eventType
              )
            );
          })
        );
      }

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
        })),
        totalLost: lost,
        liquidationEarned: liquidationEarned,
        events
      } as AaveLoan;
    }

    if (loan.protocol === DEFI_COMPOUND) {
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
          .map(value => ({ ...value, id: `${value.txHash}-${value.logIndex}` }))
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
    if (showAll || protocols.includes(DEFI_MAKERDAO)) {
      totalCollateralUsd = makerDAOVaults
        .map(({ collateral: { usdValue } }) => usdValue)
        .reduce((sum, collateralUsdValue) => sum.plus(collateralUsdValue), Zero)
        .plus(totalCollateralUsd);

      totalDebt = makerDAOVaults
        .map(({ debt: { usdValue } }) => usdValue)
        .reduce((sum, debt) => sum.plus(debt), Zero)
        .plus(totalDebt);
    }

    if (showAll || protocols.includes(DEFI_AAVE)) {
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

    if (showAll || protocols.includes(DEFI_COMPOUND)) {
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

  effectiveInterestRate: (_, { lendingBalances, yearnVaultsAssets }) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): string => {
    let { usdValue, weight } = lendingBalances(protocols, addresses)
      .filter(({ balance }) => balance.usdValue.gt(0))
      .map(({ effectiveInterestRate, balance: { usdValue } }) => {
        const n = parseFloat(effectiveInterestRate);
        return {
          weight: usdValue.multipliedBy(n),
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

    if (protocols.length === 0 || protocols.includes(DEFI_YEARN_VAULTS)) {
      const { usdValue: yUsdValue, weight: yWeight } = yearnVaultsAssets([])
        .filter(({ underlyingValue }) => underlyingValue.usdValue.gt(Zero))
        .map(({ underlyingValue: { usdValue }, roi }) => ({
          usdValue: usdValue,
          weight: usdValue.multipliedBy(parseFloat(roi))
        }))
        .reduce(
          ({ usdValue, weight: sWeight }, current) => ({
            weight: sWeight.plus(current.weight),
            usdValue: usdValue.plus(current.usdValue)
          }),
          { weight: Zero, usdValue: Zero }
        );

      usdValue = usdValue.plus(yUsdValue);
      weight = weight.plus(yWeight);
    }

    const effectiveInterestRate = weight.div(usdValue);
    return effectiveInterestRate.isNaN()
      ? '0.00%'
      : `${effectiveInterestRate.toFormat(2)}%`;
  },

  totalLendingDeposit: (
    _: DefiState,
    { lendingBalances, yearnVaultsAssets }
  ) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): BigNumber => {
    let lendingDeposit = lendingBalances(protocols, addresses)
      .map(value => value.balance.usdValue)
      .reduce((sum, usdValue) => sum.plus(usdValue), Zero);

    if (protocols.length === 0 || protocols.includes(DEFI_YEARN_VAULTS)) {
      lendingDeposit = lendingDeposit.plus(
        yearnVaultsAssets(addresses)
          .map(value => value.underlyingValue.usdValue)
          .reduce((sum, usdValue) => sum.plus(usdValue), Zero)
      );
    }
    return lendingDeposit;
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

  lendingBalances: (
    { dsrBalances, aaveBalances, compoundBalances }: DefiState,
    _dg,
    _rs,
    { 'balances/getIdentifierForSymbol': getIdentifierForSymbol }
  ) => (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ): DefiBalance[] => {
    const balances: DefiBalance[] = [];
    const showAll = protocols.length === 0;
    const allAddresses = addresses.length === 0;

    if (showAll || protocols.includes(DEFI_MAKERDAO)) {
      for (const address of Object.keys(dsrBalances.balances)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const balance = dsrBalances.balances[address];
        const currentDsr = dsrBalances.currentDsr;
        // noinspection SuspiciousTypeOfGuard
        const isBigNumber = currentDsr instanceof BigNumber;
        const format = isBigNumber ? currentDsr.toFormat(2) : 0;
        balances.push({
          address,
          protocol: DEFI_MAKERDAO,
          asset: getIdentifierForSymbol('DAI'),
          balance: { ...balance },
          effectiveInterestRate: `${format}%`
        });
      }
    }

    if (showAll || protocols.includes(DEFI_AAVE)) {
      for (const address of Object.keys(aaveBalances)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const { lending } = aaveBalances[address];

        for (const asset of Object.keys(lending)) {
          const aaveAsset = lending[asset];
          balances.push({
            address,
            protocol: DEFI_AAVE,
            asset,
            effectiveInterestRate: aaveAsset.apy,
            balance: { ...aaveAsset.balance }
          });
        }
      }
    }

    if (showAll || protocols.includes(DEFI_COMPOUND)) {
      for (const address of Object.keys(compoundBalances)) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const { lending } = compoundBalances[address];
        for (const asset of Object.keys(lending)) {
          const assetDetails = lending[asset];
          balances.push({
            address,
            protocol: DEFI_COMPOUND,
            asset,
            effectiveInterestRate: assetDetails.apy ?? '0%',
            balance: { ...assetDetails.balance }
          });
        }
      }
    }

    return sortBy(balances, 'asset');
  },

  lendingHistory: (
    { dsrHistory, aaveHistory, compoundHistory, yearnVaultsHistory }: DefiState,
    _dg,
    _rs,
    { 'balances/getIdentifierForSymbol': getIdentifierForSymbol }
  ) => (
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
            id: `${movement.txHash}-${id++}`,
            eventType: movement.movementType,
            protocol: DEFI_MAKERDAO,
            address,
            asset: getIdentifierForSymbol('DAI'),
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
          if (!isLendingEvent(event)) {
            continue;
          }

          const items = {
            id: `${event.txHash}-${event.logIndex}`,
            eventType: event.eventType,
            protocol: DEFI_AAVE,
            address,
            asset: event.asset,
            atoken: event.atoken,
            value: event.value,
            blockNumber: event.blockNumber,
            timestamp: event.timestamp,
            txHash: event.txHash,
            extras: {}
          } as DefiLendingHistory<typeof DEFI_AAVE>;
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
          id: `${event.txHash}-${event.logIndex}`,
          eventType: event.eventType,
          protocol: DEFI_COMPOUND,
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
        } as DefiLendingHistory<typeof DEFI_COMPOUND>;
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
              id: `${event.txHash}-${event.logIndex}`,
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
            } as DefiLendingHistory<typeof DEFI_YEARN_VAULTS>;
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
      section: Section,
      name: OverviewDefiProtocol,
      noLiabilities?: boolean
    ): DefiProtocolSummary | undefined => {
      const currentStatus = status(section);
      if (
        currentStatus !== Status.LOADED &&
        currentStatus !== Status.REFRESHING
      ) {
        return undefined;
      }
      const filter: SupportedDefiProtocols[] = [protocol];
      const { totalCollateralUsd, totalDebt } = noLiabilities
        ? { totalCollateralUsd: Zero, totalDebt: Zero }
        : loanSummary(filter);
      return {
        protocol: {
          name: name,
          icon: getProtcolIcon(name)
        },
        tokenInfo: null,
        assets: [],
        liabilitiesUrl: noLiabilities
          ? undefined
          : `/defi/liabilities?protocol=${protocol}`,
        depositsUrl: `/defi/deposits?protocol=${protocol}`,
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

        if (protocol === AAVE) {
          const aaveSummary = protocolSummary(
            DEFI_AAVE,
            Section.DEFI_AAVE_BALANCES,
            protocol
          );

          if (aaveSummary) {
            summary[protocol] = aaveSummary;
          }
          continue;
        }

        if (protocol === COMPOUND) {
          const compoundSummary = protocolSummary(
            DEFI_COMPOUND,
            Section.DEFI_COMPOUND_BALANCES,
            protocol
          );

          if (compoundSummary) {
            summary[protocol] = compoundSummary;
          }
          continue;
        }

        if (protocol === YEARN_FINANCE_VAULTS) {
          const compoundSummary = protocolSummary(
            DEFI_YEARN_VAULTS,
            Section.DEFI_YEARN_VAULTS_BALANCES,
            protocol,
            true
          );

          if (compoundSummary) {
            summary[protocol] = compoundSummary;
          }
          continue;
        }

        if (!summary[protocol]) {
          summary[protocol] = {
            protocol: {
              ...entry.protocol,
              icon: getProtcolIcon(protocol)
            },
            tokenInfo: {
              tokenName: entry.baseBalance.tokenName,
              tokenSymbol: entry.baseBalance.tokenSymbol
            },
            assets: [],
            totalCollateralUsd: Zero,
            totalDebtUsd: Zero,
            totalLendingDepositUsd: Zero
          };
        } else if (
          summary[protocol].tokenInfo?.tokenName !== entry.baseBalance.tokenName
        ) {
          const tokenInfo: Writeable<TokenInfo> = summary[protocol].tokenInfo!;
          tokenInfo.tokenName = `${i18n.t('defi_overview.multiple_assets')}`;
          tokenInfo.tokenSymbol = '';
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
      const filter: SupportedDefiProtocols[] = [DEFI_MAKERDAO];
      const { totalCollateralUsd, totalDebt } = loanSummary(filter);
      summary[DEFI_MAKERDAO] = {
        protocol: {
          name: MAKERDAO,
          icon: getProtcolIcon(MAKERDAO)
        },
        tokenInfo: null,
        assets: [],
        liabilitiesUrl: '/defi/liabilities?protocol=makerdao',
        depositsUrl: '/defi/deposits?protocol=makerdao',
        totalCollateralUsd,
        totalDebtUsd: totalDebt,
        totalLendingDepositUsd: totalLendingDeposit(filter, [])
      };
    }

    return sortBy(Object.values(summary), 'protocol.name');
  },

  compoundRewards: ({ compoundHistory }): ProfitLossModel[] => {
    return toProfitLossModel(compoundHistory.rewards);
  },

  compoundInterestProfit: ({ compoundHistory }): ProfitLossModel[] => {
    return toProfitLossModel(compoundHistory.interestProfit);
  },

  compoundDebtLoss: ({ compoundHistory }): ProfitLossModel[] => {
    return toProfitLossModel(compoundHistory.debtLoss);
  },

  compoundLiquidationProfit: ({ compoundHistory }): ProfitLossModel[] => {
    return toProfitLossModel(compoundHistory.liquidationProfit);
  },

  yearnVaultsProfit: ({ yearnVaultsHistory }) => (
    addresses: string[]
  ): YearnVaultProfitLoss[] => {
    const yearnVaultsProfit: { [vault: string]: YearnVaultProfitLoss } = {};
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

        if (!yearnVaultsProfit[vault]) {
          yearnVaultsProfit[vault] = {
            value: data.profitLoss,
            vault,
            asset
          };
        } else {
          yearnVaultsProfit[vault] = {
            ...yearnVaultsProfit[vault],
            value: balanceSum(yearnVaultsProfit[vault].value, data.profitLoss)
          };
        }
      }
    }
    return Object.values(yearnVaultsProfit);
  },

  yearnVaultsAssets: ({ yearnVaultsBalances }) => (
    addresses: string[]
  ): YearnVaultBalance[] => {
    const balances: { [vault: string]: YearnVaultBalance[] } = {};
    const allAddresses = addresses.length === 0;
    for (const address in yearnVaultsBalances) {
      if (!allAddresses && !addresses.includes(address)) {
        continue;
      }

      const vaults = yearnVaultsBalances[address];
      for (const key in vaults) {
        const vault = key as SupportedYearnVault;
        const balance = vaults[vault];
        if (!balance) {
          continue;
        }

        if (!balances[vault]) {
          balances[vault] = [balance];
        } else {
          balances[vault].push(balance);
        }
      }
    }

    const vaultBalances: YearnVaultAsset[] = [];
    for (const key in balances) {
      const allBalances = balances[key];
      const { underlyingToken, vaultToken, roi } = allBalances[0];

      const underlyingValue = { amount: Zero, usdValue: Zero };
      const vaultValue = { amount: Zero, usdValue: Zero };
      const values = { underlyingValue, vaultValue };
      const summary = allBalances.reduce((sum, current) => {
        return {
          vaultValue: balanceSum(sum.vaultValue, current.vaultValue),
          underlyingValue: balanceSum(
            sum.underlyingValue,
            current.underlyingValue
          )
        };
      }, values);
      vaultBalances.push({
        vault: key as SupportedYearnVault,
        underlyingToken,
        underlyingValue: summary.underlyingValue,
        vaultToken,
        vaultValue: summary.vaultValue,
        roi
      });
    }

    return vaultBalances;
  },

  aaveTotalEarned: ({ aaveHistory }) => (
    addresses: string[]
  ): ProfitLossModel[] => {
    const earned: ProfitLossModel[] = [];

    for (const address in aaveHistory) {
      if (addresses.length > 0 && !addresses.includes(address)) {
        continue;
      }
      const totalEarned = aaveHistory[address].totalEarnedInterest;
      for (const asset in totalEarned) {
        const index = earned.findIndex(e => e.asset === asset);
        if (index < 0) {
          earned.push({
            address: '',
            asset,
            value: totalEarned[asset]
          });
        } else {
          earned[index] = {
            ...earned[index],
            value: balanceSum(earned[index].value, totalEarned[asset])
          };
        }
      }
    }
    return earned;
  },

  uniswapBalances: ({ uniswapBalances }) => (
    addresses: string[]
  ): UniswapBalance[] => {
    const balances: { [poolAddress: string]: Writeable<UniswapBalance> } = {};
    for (const account in uniswapBalances) {
      if (addresses.length > 0 && !addresses.includes(account)) {
        continue;
      }
      const accountBalances = uniswapBalances[account];
      if (!accountBalances || accountBalances.length === 0) {
        continue;
      }
      for (const {
        userBalance,
        totalSupply,
        assets,
        address
      } of accountBalances) {
        const balance = balances[address];
        if (balance) {
          const oldBalance = balance.userBalance;
          balance.userBalance = {
            amount: oldBalance.amount.plus(userBalance.amount),
            usdValue: oldBalance.usdValue.plus(userBalance.usdValue)
          };

          if (balance.totalSupply !== null && totalSupply !== null) {
            balance.totalSupply = balance.totalSupply.plus(totalSupply);
          }
        } else {
          balances[address] = {
            account,
            userBalance,
            totalSupply,
            assets,
            poolAddress: address
          };
        }
      }
    }
    return Object.values(balances);
  },
  basicDexTrades: ({ uniswapTrades, balancerTrades }) => (
    addresses
  ): Trade[] => {
    function transform(
      trades: DexTrades,
      location: 'uniswap' | 'balancer'
    ): Trade[] {
      const simpleTrades: Trade[] = [];
      for (const address in trades) {
        if (addresses.length > 0 && !addresses.includes(address)) {
          continue;
        }
        const dexTrade = trades[address];
        const convertedTrades: Trade[] = dexTrade.map(trade => ({
          tradeId: trade.tradeId,
          location: location,
          amount: trade.amount,
          fee: trade.fee,
          feeCurrency: trade.feeCurrency,
          timestamp: trade.timestamp,
          baseAsset: trade.baseAsset,
          quoteAsset: trade.quoteAsset,
          rate: trade.rate,
          tradeType: 'buy',
          link: '',
          notes: '',
          ignoredInAccounting: false
        }));
        simpleTrades.push(...convertedTrades);
      }
      return simpleTrades;
    }

    const trades: Trade[] = [];
    trades.push(...transform(uniswapTrades, 'uniswap'));
    trades.push(...transform(balancerTrades, 'balancer'));
    return sortBy(trades, 'timestamp').reverse();
  },
  uniswapPoolProfit: ({ uniswapEvents }) => (
    addresses: string[]
  ): UniswapPoolProfit[] => {
    const perPoolProfit: {
      [poolAddress: string]: Writeable<UniswapPoolProfit>;
    } = {};
    for (const address in uniswapEvents) {
      if (addresses.length > 0 && !addresses.includes(address)) {
        continue;
      }

      const details = uniswapEvents[address];
      for (const detail of details) {
        const { poolAddress } = detail;
        const profit = perPoolProfit[poolAddress];
        if (profit) {
          perPoolProfit[poolAddress] = {
            ...profit,
            profitLoss0: profit.profitLoss0.plus(detail.profitLoss0),
            profitLoss1: profit.profitLoss1.plus(detail.profitLoss1),
            usdProfitLoss: profit.usdProfitLoss.plus(detail.usdProfitLoss)
          };
        } else {
          const { events: _, address, ...poolProfit } = detail;
          perPoolProfit[poolAddress] = poolProfit;
        }
      }
    }
    return Object.values(perPoolProfit);
  },
  uniswapEvents: ({ uniswapEvents }) => (addresses): UniswapEventDetails[] => {
    const eventDetails: UniswapEventDetails[] = [];
    for (const address in uniswapEvents) {
      if (addresses.length > 0 && !addresses.includes(address)) {
        continue;
      }
      const details = uniswapEvents[address];
      for (const { events, poolAddress, token0, token1 } of details) {
        for (const event of events) {
          eventDetails.push({
            ...event,
            address,
            poolAddress: poolAddress,
            token0: token0,
            token1: token1
          });
        }
      }
    }
    return eventDetails;
  },
  uniswapAddresses: ({ uniswapEvents, uniswapBalances }) => {
    return Object.keys(uniswapBalances)
      .concat(Object.keys(uniswapEvents))
      .filter(uniqueStrings);
  },
  dexTrades: ({ uniswapTrades, balancerTrades }) => (addresses): DexTrade[] => {
    const trades: DexTrade[] = [];
    for (const address in uniswapTrades) {
      if (addresses.length > 0 && !addresses.includes(address)) {
        continue;
      }
      trades.push(...uniswapTrades[address]);
    }

    for (const address in balancerTrades) {
      if (addresses.length > 0 && !addresses.includes(address)) {
        continue;
      }
      trades.push(...balancerTrades[address]);
    }
    return sortBy(trades, 'timestamp').reverse();
  },
  airdrops: ({ airdrops }) => (addresses): Airdrop[] => {
    const data: Airdrop[] = [];
    for (const address in airdrops) {
      if (addresses.length > 0 && !addresses.includes(address)) {
        continue;
      }
      const airdrop = airdrops[address];
      for (const source in airdrop) {
        const element = airdrop[source as AirdropType];
        if (source === AIRDROP_POAP) {
          const details = element as PoapDelivery[];
          data.push({
            address,
            source: source as AirdropType,
            details: details.map(value => ({
              amount: '1',
              link: value.link,
              name: value.name,
              event: value.event
            }))
          });
        } else {
          const { amount, asset, link } = element as AirdropDetail;
          data.push({
            address,
            amount,
            link,
            source: source as AirdropType,
            asset
          });
        }
      }
    }
    return data;
  },
  airdropAddresses: ({ airdrops }) => Object.keys(airdrops),
  [GETTER_UNISWAP_ASSETS]: ({ uniswapEvents, uniswapBalances }) => {
    const pools: UniswapPool[] = [];
    const known: { [address: string]: boolean } = {};
    for (const account in uniswapBalances) {
      const accountBalances = uniswapBalances[account];
      if (!accountBalances || accountBalances.length === 0) {
        continue;
      }
      for (const { assets, address } of accountBalances) {
        if (known[address]) {
          continue;
        }
        known[address] = true;
        pools.push({
          address,
          assets: assets.map(({ asset }) => asset)
        });
      }
    }

    for (const address in uniswapEvents) {
      const details = uniswapEvents[address];
      for (const { poolAddress, token0, token1 } of details) {
        if (known[poolAddress]) {
          continue;
        }
        known[poolAddress] = true;
        pools.push({
          address: poolAddress,
          assets: [token0, token1]
        });
      }
    }
    return pools;
  },

  [GETTER_BALANCER_BALANCES]: ({ balancerBalances }) => {
    const balances: BalancerBalanceWithOwner[] = [];
    for (const address in balancerBalances) {
      for (const balance of balancerBalances[address]) {
        balances.push({
          ...balance,
          owner: address
        });
      }
    }
    return balances;
  },
  balancerAddresses: ({ balancerBalances }) => Object.keys(balancerBalances),
  balancerEvents: (
    { balancerEvents },
    _dg,
    _rs,
    { 'balances/assetSymbol': assetSymbol }
  ) => (addresses): BalancerEvent[] => {
    const events: BalancerEvent[] = [];
    filterAddresses(balancerEvents, addresses, item => {
      for (let i = 0; i < item.length; i++) {
        const poolDetail = item[i];
        events.push(
          ...poolDetail.events.map(value => ({
            ...value,
            pool: {
              name: poolDetail.poolTokens
                .map(pool => assetSymbol(pool.token))
                .join('/'),
              address: poolDetail.poolAddress
            }
          }))
        );
      }
    });
    return events;
  },
  balancerPools: (
    _,
    { balancerBalances, balancerEvents },
    _rs,
    { 'balances/assetSymbol': assetSymbol }
  ) => {
    const pools: { [address: string]: Pool } = {};
    const events = balancerEvents([]);

    for (const balance of balancerBalances) {
      if (pools[balance.address]) {
        continue;
      }
      pools[balance.address] = {
        name: balance.tokens.map(token => assetSymbol(token.token)).join('/'),
        address: balance.address
      };
    }

    for (const event of events) {
      const pool = event.pool;
      if (!pool || pools[pool.address]) {
        continue;
      }
      pools[pool.address] = {
        name: pool.name,
        address: pool.address
      };
    }
    return Object.values(pools);
  },
  balancerProfitLoss: (
    { balancerEvents },
    _dg,
    _rs,
    { 'balances/assetSymbol': assetSymbol }
  ) => addresses => {
    const balancerProfitLoss: { [pool: string]: BalancerProfitLoss } = {};
    filterAddresses(balancerEvents, addresses, item => {
      for (let i = 0; i < item.length; i++) {
        const entry = item[i];
        if (!balancerProfitLoss[entry.poolAddress]) {
          balancerProfitLoss[entry.poolAddress] = {
            pool: {
              address: entry.poolAddress,
              name: entry.poolTokens
                .map(token => assetSymbol(token.token))
                .join('/')
            },
            tokens: entry.poolTokens.map(token => assetIdentifier(token.token)),
            profitLossAmount: entry.profitLossAmounts,
            usdProfitLoss: entry.usdProfitLoss
          };
        }
      }
    });
    return Object.values(balancerProfitLoss);
  }
};
