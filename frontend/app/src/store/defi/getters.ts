import { AddressIndexed, Balance, BigNumber } from '@rotki/common';
import { DefiAccount } from '@rotki/common/lib/account';
import { Blockchain, DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  AaveBorrowingEventType,
  AaveEvent,
  AaveHistoryEvents,
  AaveHistoryTotal,
  AaveLending,
  AaveLendingEventType,
  isAaveLiquidationEvent
} from '@rotki/common/lib/defi/aave';
import {
  BalancerBalanceWithOwner,
  BalancerEvent,
  BalancerProfitLoss,
  Pool
} from '@rotki/common/lib/defi/balancer';
import { DexTrade } from '@rotki/common/lib/defi/dex';
import {
  XswapBalance,
  XswapEventDetails,
  XswapPool,
  XswapPoolProfit
} from '@rotki/common/lib/defi/xswap';
import sortBy from 'lodash/sortBy';
import { explorerUrls } from '@/components/helper/asset-urls';
import { truncateAddress } from '@/filters';
import i18n from '@/i18n';
import { ProtocolVersion } from '@/services/defi/consts';
import { CompoundLoan } from '@/services/defi/types/compound';
import { DEPOSIT } from '@/services/defi/types/consts';
import {
  YearnVaultAsset,
  YearnVaultBalance,
  YearnVaultProfitLoss,
  YearnVaultsHistory
} from '@/services/defi/types/yearn';
import { Trade } from '@/services/history/types';
import { Section, Status } from '@/store/const';
import {
  AAVE,
  AIRDROP_POAP,
  COMPOUND,
  getProtcolIcon,
  GETTER_BALANCER_BALANCES,
  GETTER_UNISWAP_ASSETS,
  LIQUITY,
  MAKERDAO_DSR,
  MAKERDAO_VAULTS,
  YEARN_FINANCE_VAULTS,
  YEARN_FINANCE_VAULTS_V2
} from '@/store/defi/const';
import { LiquityLoan } from '@/store/defi/liquity/types';
import {
  AaveLoan,
  Airdrop,
  AirdropDetail,
  AirdropType,
  BaseDefiBalance,
  Collateral,
  DefiBalance,
  DefiLendingHistory,
  DefiLoan,
  DefiProtocolSummary,
  DefiState,
  DexTrades,
  LoanSummary,
  MakerDAOVaultModel,
  OverviewDefiProtocol,
  PoapDelivery,
  ProfitLossModel,
  TokenInfo
} from '@/store/defi/types';
import { balanceUsdValueSum, toProfitLossModel } from '@/store/defi/utils';
import {
  getBalances,
  getEventDetails,
  getPoolProfit,
  getPools
} from '@/store/defi/xswap-utils';
import { SettingsState } from '@/store/settings/state';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { filterAddresses } from '@/store/utils';
import { Writeable } from '@/types';
import { assert } from '@/utils/assertions';
import { Zero } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';

function isLendingEvent(value: AaveHistoryEvents): value is AaveEvent {
  const lending: string[] = Object.keys(AaveLendingEventType);
  return lending.indexOf(value.eventType) !== -1;
}

export namespace DefiGetterTypes {
  export type YearnVaultProfitType = (
    addresses: string[],
    version: ProtocolVersion
  ) => YearnVaultProfitLoss[];

  export type YearnVaultAssetType = (
    addresses: string[],
    version: ProtocolVersion
  ) => YearnVaultAsset[];
}

interface DefiGetters {
  totalUsdEarned: (protocols: DefiProtocol[], addresses: string[]) => BigNumber;
  totalLendingDeposit: (
    protocols: DefiProtocol[],
    addresses: string[]
  ) => BigNumber;
  loan: (
    identifier: string
  ) => MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan | null;
  defiAccounts: (protocols: DefiProtocol[]) => DefiAccount[];
  loans: (protocols: DefiProtocol[]) => DefiLoan[];
  loanSummary: (protocol: DefiProtocol[]) => LoanSummary;
  effectiveInterestRate: (
    protocols: DefiProtocol[],
    addresses: string[]
  ) => string;
  aggregatedLendingBalances: (
    protocols: DefiProtocol[],
    addresses: string[]
  ) => BaseDefiBalance[];
  lendingBalances: (
    protocols: DefiProtocol[],
    addresses: string[]
  ) => DefiBalance[];
  lendingHistory: (
    protocols: DefiProtocol[],
    addresses: string[]
  ) => DefiLendingHistory<DefiProtocol>[];
  defiOverview: DefiProtocolSummary[];
  compoundRewards: ProfitLossModel[];
  compoundInterestProfit: ProfitLossModel[];
  compoundLiquidationProfit: ProfitLossModel[];
  compoundDebtLoss: ProfitLossModel[];
  yearnVaultsProfit: DefiGetterTypes.YearnVaultProfitType;
  yearnVaultsAssets: DefiGetterTypes.YearnVaultAssetType;
  aaveTotalEarned: (addresses: string[]) => ProfitLossModel[];
  uniswapBalances: (addresses: string[]) => XswapBalance[];
  basicDexTrades: (addresses: string[]) => Trade[];
  uniswapPoolProfit: (addresses: string[]) => XswapPoolProfit[];
  uniswapEvents: (addresses: string[]) => XswapEventDetails[];
  uniswapAddresses: string[];
  dexTrades: (addresses: string[]) => DexTrade[];
  airdrops: (addresses: string[]) => Airdrop[];
  airdropAddresses: string[];
  [GETTER_UNISWAP_ASSETS]: XswapPool[];
  [GETTER_BALANCER_BALANCES]: BalancerBalanceWithOwner[];
  balancerAddresses: string[];
  balancerEvents: (addresses: string[]) => BalancerEvent[];
  balancerPools: Pool[];
  balancerProfitLoss: (addresses: string[]) => BalancerProfitLoss[];
}

export const getters: Getters<DefiState, DefiGetters, RotkehlchenState, any> = {
  totalUsdEarned:
    ({
      dsrHistory,
      aaveHistory,
      compoundHistory,
      yearnVaultsHistory,
      yearnVaultsV2History
    }: DefiState) =>
    (protocols: DefiProtocol[], addresses: string[]): BigNumber => {
      let total = Zero;
      const showAll = protocols.length === 0;
      const allAddresses = addresses.length === 0;

      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
        for (const address of Object.keys(dsrHistory)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }
          total = total.plus(dsrHistory[address].gainSoFar.usdValue);
        }
      }

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
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

      if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
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

      function yearnTotalEarned(vaultsHistory: YearnVaultsHistory): BigNumber {
        let yearnEarned = Zero;
        for (const address in vaultsHistory) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }
          const accountVaults = vaultsHistory[address];
          for (const vault in accountVaults) {
            const vaultData = accountVaults[vault];
            if (!vaultData) {
              continue;
            }
            yearnEarned = yearnEarned.plus(vaultData.profitLoss.usdValue);
          }
        }
        return yearnEarned;
      }

      if (showAll || protocols.includes(DefiProtocol.YEARN_VAULTS)) {
        total = total.plus(yearnTotalEarned(yearnVaultsHistory));
      }

      if (showAll || protocols.includes(DefiProtocol.YEARN_VAULTS_V2)) {
        total = total.plus(yearnTotalEarned(yearnVaultsV2History));
      }
      return total;
    },

  defiAccounts:
    ({
      aaveBalances,
      aaveHistory,
      dsrBalances,
      dsrHistory,
      compoundBalances,
      compoundHistory,
      yearnVaultsBalances,
      yearnVaultsHistory,
      yearnVaultsV2Balances,
      yearnVaultsV2History
    }: DefiState) =>
    (protocols: DefiProtocol[]): DefiAccount[] => {
      const getProtocolAddresses = (
        protocol: DefiProtocol,
        balances: AddressIndexed<any>,
        history: AddressIndexed<any> | string[]
      ) => {
        const addresses: string[] = [];
        if (protocols.length === 0 || protocols.includes(protocol)) {
          const uniqueAddresses: string[] = [
            ...Object.keys(balances),
            ...(Array.isArray(history) ? history : Object.keys(history))
          ].filter(uniqueStrings);
          addresses.push(...uniqueAddresses);
        }
        return addresses;
      };

      const addresses: {
        [key in Exclude<
          DefiProtocol,
          | DefiProtocol.MAKERDAO_VAULTS
          | DefiProtocol.UNISWAP
          | DefiProtocol.LIQUITY
        >]: string[];
      } = {
        [DefiProtocol.MAKERDAO_DSR]: [],
        [DefiProtocol.AAVE]: [],
        [DefiProtocol.COMPOUND]: [],
        [DefiProtocol.YEARN_VAULTS]: [],
        [DefiProtocol.YEARN_VAULTS_V2]: []
      };

      addresses[DefiProtocol.AAVE] = getProtocolAddresses(
        DefiProtocol.AAVE,
        aaveBalances,
        aaveHistory
      );

      addresses[DefiProtocol.COMPOUND] = getProtocolAddresses(
        DefiProtocol.COMPOUND,
        compoundBalances,
        compoundHistory.events.map(({ address }) => address)
      );

      addresses[DefiProtocol.YEARN_VAULTS] = getProtocolAddresses(
        DefiProtocol.YEARN_VAULTS,
        yearnVaultsBalances,
        yearnVaultsHistory
      );

      addresses[DefiProtocol.YEARN_VAULTS_V2] = getProtocolAddresses(
        DefiProtocol.YEARN_VAULTS_V2,
        yearnVaultsV2Balances,
        yearnVaultsV2History
      );

      addresses[DefiProtocol.MAKERDAO_DSR] = getProtocolAddresses(
        DefiProtocol.MAKERDAO_DSR,
        dsrBalances.balances,
        dsrHistory
      );

      const accounts: { [address: string]: DefiAccount } = {};
      for (const protocol in addresses) {
        const selectedProtocol = protocol as Exclude<
          DefiProtocol,
          | DefiProtocol.MAKERDAO_VAULTS
          | DefiProtocol.UNISWAP
          | DefiProtocol.LIQUITY
        >;
        const perProtocolAddresses = addresses[selectedProtocol];
        for (const address of perProtocolAddresses) {
          if (accounts[address]) {
            accounts[address].protocols.push(selectedProtocol);
          } else {
            accounts[address] = {
              address,
              chain: Blockchain.ETH,
              protocols: [selectedProtocol]
            };
          }
        }
      }

      return Object.values(accounts);
    },

  loans:
    (
      {
        aaveBalances,
        aaveHistory,
        makerDAOVaults,
        compoundBalances,
        compoundHistory: { events },
        liquity
      }: DefiState,
      _dg,
      _rs,
      { 'balances/assetInfo': assetInfo }
    ) =>
    (protocols: DefiProtocol[]): DefiLoan[] => {
      const loans: DefiLoan[] = [];
      const showAll = protocols.length === 0;

      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_VAULTS)) {
        loans.push(
          ...makerDAOVaults.map(
            value =>
              ({
                identifier: `${value.identifier}`,
                protocol: DefiProtocol.MAKERDAO_VAULTS
              } as DefiLoan)
          )
        );
      }

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
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
              protocol: DefiProtocol.AAVE,
              owner: address,
              asset
            });
            knownAssets.push(asset);
          }
        }

        for (const address in aaveHistory) {
          const { events } = aaveHistory[address];
          const borrowEvents: string[] = Object.values(AaveBorrowingEventType);
          const historyAssets = events
            .filter(e => borrowEvents.includes(e.eventType))
            .map(event =>
              isAaveLiquidationEvent(event) ? event.principalAsset : event.asset
            )
            .filter(uniqueStrings)
            .filter(asset => !knownAssets.includes(asset));

          for (const asset of historyAssets) {
            const symbol = assetInfo(asset)?.symbol ?? asset;
            loans.push({
              identifier: `${symbol} - ${truncateAddress(address, 6)}`,
              protocol: DefiProtocol.AAVE,
              owner: address,
              asset
            });
          }
        }
      }

      if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
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
              protocol: DefiProtocol.COMPOUND,
              owner: address,
              asset
            });
          });
      }

      if (showAll || protocols.includes(DefiProtocol.LIQUITY)) {
        assert(liquity);
        const { events, balances } = liquity;
        const balanceAddress = Object.keys(balances);
        const eventAddresses = Object.keys(events);

        loans.push(
          ...[...balanceAddress, ...eventAddresses]
            .filter(uniqueStrings)
            .map(address => {
              let troveId = 0;
              if (balances[address]) {
                troveId = balances[address].troveId;
              }
              return {
                identifier: `Trove ${troveId} - ${truncateAddress(address, 6)}`,
                protocol: DefiProtocol.LIQUITY,
                owner: address,
                asset: ''
              };
            })
        );
      }

      return sortBy(loans, 'identifier');
    },

  loan:
    (
      {
        makerDAOVaults,
        makerDAOVaultDetails,
        aaveBalances,
        aaveHistory,
        compoundBalances,
        compoundHistory: { events },
        liquity
      }: DefiState,
      { loans }
    ) =>
    (
      identifier?: string
    ): MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan | null => {
      const id = identifier?.toLocaleLowerCase();
      const loan = loans([]).find(
        loan => loan.identifier.toLocaleLowerCase() === id
      );

      if (!loan) {
        return null;
      }

      if (loan.protocol === DefiProtocol.MAKERDAO_VAULTS) {
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

      if (loan.protocol === DefiProtocol.AAVE) {
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
            if (!isAaveLiquidationEvent(event)) {
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
              const isAsset: boolean = !isAaveLiquidationEvent(event)
                ? event.asset === asset
                : event.principalAsset === asset;
              return (
                isAsset &&
                Object.values(AaveBorrowingEventType).find(
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

      if (loan.protocol === DefiProtocol.COMPOUND) {
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
            .filter(
              event => event.asset === asset || event.eventType === 'comp'
            )
            .filter(({ address }) => address === owner)
            .filter(({ eventType }) => !['mint', 'redeem'].includes(eventType))
            .map(value => ({
              ...value,
              id: `${value.txHash}-${value.logIndex}`
            }))
        } as CompoundLoan;
      }

      if (loan.protocol === DefiProtocol.LIQUITY) {
        assert(liquity);
        assert(loan.owner);
        const { owner } = loan;
        const { balances, events } = liquity;

        return {
          owner: owner,
          protocol: loan.protocol,
          balance: balances[owner],
          events: events[owner] ?? []
        } as LiquityLoan;
      }

      return null;
    },

  loanSummary:
    ({ makerDAOVaults, aaveBalances, compoundBalances, liquity }: DefiState) =>
    (protocols: DefiProtocol[]): LoanSummary => {
      let totalCollateralUsd = Zero;
      let totalDebt = Zero;

      const showAll = protocols.length === 0;
      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_VAULTS)) {
        totalCollateralUsd = makerDAOVaults
          .map(({ collateral: { usdValue } }) => usdValue)
          .reduce(
            (sum, collateralUsdValue) => sum.plus(collateralUsdValue),
            Zero
          )
          .plus(totalCollateralUsd);

        totalDebt = makerDAOVaults
          .map(({ debt: { usdValue } }) => usdValue)
          .reduce((sum, debt) => sum.plus(debt), Zero)
          .plus(totalDebt);
      }

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
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

      if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
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

      if (showAll || protocols.includes(DefiProtocol.LIQUITY)) {
        const balances = liquity!!.balances;
        for (const address in balances) {
          const balance = balances[address];
          const { collateral, debt } = balance;
          totalCollateralUsd = collateral.usdValue.plus(totalCollateralUsd);
          totalDebt = debt.usdValue.plus(totalDebt);
        }
      }

      return { totalCollateralUsd, totalDebt };
    },

  effectiveInterestRate:
    (_, { lendingBalances, yearnVaultsAssets }) =>
    (protocols: DefiProtocol[], addresses: string[]): string => {
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

      function yearnData(version: ProtocolVersion = ProtocolVersion.V1): {
        weight: BigNumber;
        usdValue: BigNumber;
      } {
        return yearnVaultsAssets([], version)
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
      }

      if (
        protocols.length === 0 ||
        protocols.includes(DefiProtocol.YEARN_VAULTS)
      ) {
        const { usdValue: yUsdValue, weight: yWeight } = yearnData();
        usdValue = usdValue.plus(yUsdValue);
        weight = weight.plus(yWeight);
      }

      if (
        protocols.length === 0 ||
        protocols.includes(DefiProtocol.YEARN_VAULTS_V2)
      ) {
        const { usdValue: yUsdValue, weight: yWeight } = yearnData();
        usdValue = usdValue.plus(yUsdValue);
        weight = weight.plus(yWeight);
      }

      const effectiveInterestRate = weight.div(usdValue);
      return effectiveInterestRate.isNaN()
        ? '0.00%'
        : `${effectiveInterestRate.toFormat(2)}%`;
    },

  totalLendingDeposit:
    (_: DefiState, { lendingBalances, yearnVaultsAssets }) =>
    (protocols: DefiProtocol[], addresses: string[]): BigNumber => {
      let lendingDeposit = lendingBalances(protocols, addresses)
        .map(value => value.balance.usdValue)
        .reduce((sum, usdValue) => sum.plus(usdValue), Zero);

      function getYearnDeposit(version: ProtocolVersion = ProtocolVersion.V1) {
        return yearnVaultsAssets(addresses, version)
          .map(value => value.underlyingValue.usdValue)
          .reduce((sum, usdValue) => sum.plus(usdValue), Zero);
      }

      if (
        protocols.length === 0 ||
        protocols.includes(DefiProtocol.YEARN_VAULTS)
      ) {
        lendingDeposit = lendingDeposit.plus(getYearnDeposit());
      }

      if (
        protocols.length === 0 ||
        protocols.includes(DefiProtocol.YEARN_VAULTS_V2)
      ) {
        lendingDeposit = lendingDeposit.plus(
          getYearnDeposit(ProtocolVersion.V2)
        );
      }

      return lendingDeposit;
    },

  aggregatedLendingBalances:
    (_, { lendingBalances }) =>
    (protocols: DefiProtocol[], addresses: string[]): BaseDefiBalance[] => {
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

  lendingBalances:
    (
      { dsrBalances, aaveBalances, compoundBalances }: DefiState,
      _dg,
      _rs,
      { 'balances/getIdentifierForSymbol': getIdentifierForSymbol }
    ) =>
    (protocols: DefiProtocol[], addresses: string[]): DefiBalance[] => {
      const balances: DefiBalance[] = [];
      const showAll = protocols.length === 0;
      const allAddresses = addresses.length === 0;

      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
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
            protocol: DefiProtocol.MAKERDAO_DSR,
            asset: getIdentifierForSymbol('DAI'),
            balance: { ...balance },
            effectiveInterestRate: `${format}%`
          });
        }
      }

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
        for (const address of Object.keys(aaveBalances)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }
          const { lending } = aaveBalances[address];

          for (const asset of Object.keys(lending)) {
            const aaveAsset = lending[asset];
            balances.push({
              address,
              protocol: DefiProtocol.AAVE,
              asset,
              effectiveInterestRate: aaveAsset.apy,
              balance: { ...aaveAsset.balance }
            });
          }
        }
      }

      if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
        for (const address of Object.keys(compoundBalances)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }
          const { lending } = compoundBalances[address];
          for (const asset of Object.keys(lending)) {
            const assetDetails = lending[asset];
            balances.push({
              address,
              protocol: DefiProtocol.COMPOUND,
              asset,
              effectiveInterestRate: assetDetails.apy ?? '0%',
              balance: { ...assetDetails.balance }
            });
          }
        }
      }

      return sortBy(balances, 'asset');
    },

  lendingHistory:
    (
      {
        dsrHistory,
        aaveHistory,
        compoundHistory,
        yearnVaultsHistory,
        yearnVaultsV2History
      }: DefiState,
      _dg,
      _rs,
      { 'balances/getIdentifierForSymbol': getIdentifierForSymbol }
    ) =>
    (
      protocols: DefiProtocol[],
      addresses: string[]
    ): DefiLendingHistory<DefiProtocol>[] => {
      const defiLendingHistory: DefiLendingHistory<DefiProtocol>[] = [];
      const showAll = protocols.length === 0;
      const allAddresses = addresses.length === 0;
      let id = 1;

      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
        for (const address of Object.keys(dsrHistory)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }

          const history = dsrHistory[address];

          for (const movement of history.movements) {
            defiLendingHistory.push({
              id: `${movement.txHash}-${id++}`,
              eventType: movement.movementType,
              protocol: DefiProtocol.MAKERDAO_DSR,
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

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
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
              protocol: DefiProtocol.AAVE,
              address,
              asset: event.asset,
              atoken: event.atoken,
              value: event.value,
              blockNumber: event.blockNumber,
              timestamp: event.timestamp,
              txHash: event.txHash,
              extras: {}
            } as DefiLendingHistory<typeof DefiProtocol.AAVE>;
            defiLendingHistory.push(items);
          }
        }
      }

      if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
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
            protocol: DefiProtocol.COMPOUND,
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
          } as DefiLendingHistory<typeof DefiProtocol.COMPOUND>;
          defiLendingHistory.push(item);
        }
      }

      function yearnHistory(version: ProtocolVersion = ProtocolVersion.V1) {
        const isV1 = version === ProtocolVersion.V1;
        const vaultsHistory = isV1 ? yearnVaultsHistory : yearnVaultsV2History;
        for (const address in vaultsHistory) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }
          const history = vaultsHistory[address];

          for (const vault in history) {
            const data = history[vault];
            if (!data || !data.events || data.events.length === 0) {
              continue;
            }
            for (const event of data.events) {
              const item = {
                id: `${event.txHash}-${event.logIndex}`,
                eventType: event.eventType,
                protocol: isV1
                  ? DefiProtocol.YEARN_VAULTS
                  : DefiProtocol.YEARN_VAULTS_V2,
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
              } as DefiLendingHistory<typeof DefiProtocol.YEARN_VAULTS>;
              defiLendingHistory.push(item);
            }
          }
        }
      }

      if (showAll || protocols.includes(DefiProtocol.YEARN_VAULTS)) {
        yearnHistory();
      }

      if (showAll || protocols.includes(DefiProtocol.YEARN_VAULTS_V2)) {
        yearnHistory(ProtocolVersion.V2);
      }
      return sortBy(defiLendingHistory, 'timestamp').reverse();
    },

  defiOverview: (
    { allProtocols },
    { loanSummary, totalLendingDeposit },
    _,
    { status }
  ) => {
    function shouldDisplay(summary: DefiProtocolSummary) {
      const lending = summary.totalLendingDepositUsd.gt(0);
      const debt = summary.totalDebtUsd.gt(0);
      const balance = summary.balanceUsd && summary.balanceUsd.gt(0);
      const collateral = summary.totalCollateralUsd.gt(0);
      return lending || debt || balance || collateral;
    }

    const protocolSummary = (
      protocol: DefiProtocol,
      section: Section,
      name: OverviewDefiProtocol,
      noLiabilities?: boolean,
      noDeposits?: boolean
    ): DefiProtocolSummary | undefined => {
      const currentStatus = status(section);
      if (
        currentStatus !== Status.LOADED &&
        currentStatus !== Status.REFRESHING
      ) {
        return undefined;
      }
      const filter: DefiProtocol[] = [protocol];
      const { totalCollateralUsd, totalDebt } = noLiabilities
        ? { totalCollateralUsd: Zero, totalDebt: Zero }
        : loanSummary(filter);
      return {
        protocol: {
          name: name,
          icon: getProtcolIcon(name)
        },
        liabilities: !noLiabilities,
        deposits: !noDeposits,
        tokenInfo: null,
        assets: [],
        liabilitiesUrl: noLiabilities
          ? undefined
          : `/defi/liabilities?protocol=${protocol}`,
        depositsUrl: noDeposits
          ? undefined
          : `/defi/deposits?protocol=${protocol}`,
        totalCollateralUsd,
        totalDebtUsd: totalDebt,
        totalLendingDepositUsd: noDeposits
          ? Zero
          : totalLendingDeposit(filter, [])
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
            DefiProtocol.AAVE,
            Section.DEFI_AAVE_BALANCES,
            protocol
          );

          if (aaveSummary && shouldDisplay(aaveSummary)) {
            summary[protocol] = aaveSummary;
          }
          continue;
        }

        if (protocol === COMPOUND) {
          const compoundSummary = protocolSummary(
            DefiProtocol.COMPOUND,
            Section.DEFI_COMPOUND_BALANCES,
            protocol
          );

          if (compoundSummary && shouldDisplay(compoundSummary)) {
            summary[protocol] = compoundSummary;
          }
          continue;
        }

        if (protocol === YEARN_FINANCE_VAULTS) {
          const yearnVaultsSummary = protocolSummary(
            DefiProtocol.YEARN_VAULTS,
            Section.DEFI_YEARN_VAULTS_BALANCES,
            protocol,
            true
          );

          if (yearnVaultsSummary && shouldDisplay(yearnVaultsSummary)) {
            summary[protocol] = yearnVaultsSummary;
          }
          continue;
        }

        if (protocol === LIQUITY) {
          const liquity = protocolSummary(
            DefiProtocol.LIQUITY,
            Section.DEFI_LIQUITY_BALANCES,
            protocol,
            false,
            true
          );

          if (liquity && shouldDisplay(liquity)) {
            summary[protocol] = liquity;
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
            deposits: false,
            liabilities: false,
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

    const overviewStatus = status(Section.DEFI_OVERVIEW);
    if (
      overviewStatus === Status.LOADED ||
      overviewStatus === Status.REFRESHING
    ) {
      const filter: DefiProtocol[] = [DefiProtocol.MAKERDAO_DSR];
      const makerDAODSRSummary: DefiProtocolSummary = {
        protocol: {
          name: MAKERDAO_DSR,
          icon: getProtcolIcon(MAKERDAO_DSR)
        },
        tokenInfo: null,
        assets: [],
        depositsUrl: '/defi/deposits?protocol=makerdao',
        deposits: true,
        liabilities: false,
        totalCollateralUsd: Zero,
        totalDebtUsd: Zero,
        totalLendingDepositUsd: totalLendingDeposit(filter, [])
      };

      const { totalCollateralUsd, totalDebt } = loanSummary([
        DefiProtocol.MAKERDAO_VAULTS
      ]);
      const makerDAOVaultSummary: DefiProtocolSummary = {
        protocol: {
          name: MAKERDAO_VAULTS,
          icon: getProtcolIcon(MAKERDAO_VAULTS)
        },
        tokenInfo: null,
        assets: [],
        deposits: false,
        liabilities: true,
        liabilitiesUrl: '/defi/liabilities?protocol=makerdao',
        totalDebtUsd: totalDebt,
        totalCollateralUsd,
        totalLendingDepositUsd: Zero
      };

      if (shouldDisplay(makerDAODSRSummary)) {
        summary[DefiProtocol.MAKERDAO_DSR] = makerDAODSRSummary;
      }

      if (shouldDisplay(makerDAOVaultSummary)) {
        summary[DefiProtocol.MAKERDAO_VAULTS] = makerDAOVaultSummary;
      }

      const yearnV2Summary = protocolSummary(
        DefiProtocol.YEARN_VAULTS_V2,
        Section.DEFI_YEARN_VAULTS_V2_BALANCES,
        YEARN_FINANCE_VAULTS_V2,
        true
      );
      if (yearnV2Summary && shouldDisplay(yearnV2Summary)) {
        summary[DefiProtocol.YEARN_VAULTS_V2] = yearnV2Summary;
      }
    }

    return sortBy(Object.values(summary), 'protocol.name').filter(
      value => value.balanceUsd || value.deposits || value.liabilities
    );
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

  yearnVaultsProfit:
    (
      { yearnVaultsHistory, yearnVaultsV2History },
      _dg,
      _rs,
      { 'balances/assetSymbol': assetSymbol }
    ) =>
    (
      addresses: string[],
      version: ProtocolVersion = ProtocolVersion.V1
    ): YearnVaultProfitLoss[] => {
      const vaultsHistory =
        version === ProtocolVersion.V1
          ? yearnVaultsHistory
          : yearnVaultsV2History;
      const yearnVaultsProfit: { [vault: string]: YearnVaultProfitLoss } = {};
      const allAddresses = addresses.length === 0;
      for (const address in vaultsHistory) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const history = vaultsHistory[address];
        for (const vault in history) {
          const data = history[vault];
          if (!data) {
            continue;
          }

          const events = data.events.filter(
            event => event.eventType === DEPOSIT
          );
          const asset = events && events.length > 0 ? events[0].fromAsset : '';

          if (!yearnVaultsProfit[vault]) {
            let vaultName = vault;
            if (vault.startsWith('_ceth_')) {
              vaultName = `${assetSymbol(vault)} Vault`;
            }

            yearnVaultsProfit[vault] = {
              value: data.profitLoss,
              vault: vaultName,
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

  yearnVaultsAssets:
    (
      { yearnVaultsBalances, yearnVaultsV2Balances },
      _dg,
      _rs,
      { 'balances/assetSymbol': assetSymbol }
    ) =>
    (
      addresses: string[],
      version: ProtocolVersion = ProtocolVersion.V1
    ): YearnVaultAsset[] => {
      const vaultsBalances =
        version === ProtocolVersion.V1
          ? yearnVaultsBalances
          : yearnVaultsV2Balances;
      const balances: { [vault: string]: YearnVaultBalance[] } = {};
      const allAddresses = addresses.length === 0;
      for (const address in vaultsBalances) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }

        const vaults = vaultsBalances[address];
        for (const vault in vaults) {
          let vaultName = vault;

          if (vault.startsWith('0x')) {
            const tokenSymbol = assetSymbol(vaults[vault].vaultToken);
            vaultName = `${tokenSymbol} Vault`;
          }

          const balance = vaults[vault];
          if (!balance) {
            continue;
          }

          if (!balances[vaultName]) {
            balances[vaultName] = [balance];
          } else {
            balances[vaultName].push(balance);
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
          vault: key,
          version,
          underlyingToken,
          underlyingValue: summary.underlyingValue,
          vaultToken,
          vaultValue: summary.vaultValue,
          roi
        });
      }

      return vaultBalances;
    },

  aaveTotalEarned:
    ({ aaveHistory }) =>
    (addresses: string[]): ProfitLossModel[] => {
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

  uniswapBalances:
    ({ uniswapBalances }) =>
    (addresses: string[]): XswapBalance[] => {
      return getBalances(uniswapBalances, addresses);
    },
  basicDexTrades:
    ({ uniswapTrades, balancerTrades, sushiswap }, _r, { settings, history }) =>
    (addresses): Trade[] => {
      const ignoredTrades = history!.ignored.trades ?? [];
      const {
        explorers: { ETH }
      }: SettingsState = settings!;
      const txUrl = ETH?.transaction ?? explorerUrls.ETH.transaction;
      function transform(
        trades: DexTrades,
        location: 'uniswap' | 'balancer' | 'sushiswap'
      ): Trade[] {
        const simpleTrades: Trade[] = [];
        for (const address in trades) {
          if (addresses.length > 0 && !addresses.includes(address)) {
            continue;
          }
          const dexTrade = trades[address];
          const linkUrl = txUrl.endsWith('/')
            ? `${txUrl}${dexTrade[0].txHash}`
            : `${txUrl}/${dexTrade[0].txHash}`;
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
            link: linkUrl,
            notes: '',
            ignoredInAccounting: ignoredTrades.includes(trade.tradeId)
          }));
          simpleTrades.push(...convertedTrades);
        }
        return simpleTrades;
      }

      const trades: Trade[] = [];
      trades.push(...transform(uniswapTrades, 'uniswap'));
      trades.push(...transform(balancerTrades, 'balancer'));
      if (sushiswap) {
        trades.push(...transform(sushiswap.trades, 'sushiswap'));
      }
      return sortBy(trades, 'timestamp').reverse();
    },
  uniswapPoolProfit:
    ({ uniswapEvents }) =>
    (addresses: string[]): XswapPoolProfit[] => {
      return getPoolProfit(uniswapEvents, addresses);
    },
  uniswapEvents:
    ({ uniswapEvents }) =>
    (addresses): XswapEventDetails[] => {
      return getEventDetails(uniswapEvents, addresses);
    },
  uniswapAddresses: ({ uniswapEvents, uniswapBalances }) => {
    return Object.keys(uniswapBalances)
      .concat(Object.keys(uniswapEvents))
      .filter(uniqueStrings);
  },
  dexTrades:
    ({ uniswapTrades, balancerTrades, sushiswap }) =>
    (addresses): DexTrade[] => {
      const trades: DexTrade[] = [];
      const addTrades = (
        dexTrades: DexTrades,
        addresses: string[],
        trades: DexTrade[]
      ) => {
        for (const address in dexTrades) {
          if (addresses.length > 0 && !addresses.includes(address)) {
            continue;
          }
          trades.push(...dexTrades[address]);
        }
      };
      addTrades(uniswapTrades, addresses, trades);
      addTrades(balancerTrades, addresses, trades);
      if (sushiswap) {
        addTrades(sushiswap.trades, addresses, trades);
      }

      return sortBy(trades, 'timestamp').reverse();
    },
  airdrops:
    ({ airdrops }) =>
    (addresses): Airdrop[] => {
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
    return getPools(uniswapBalances, uniswapEvents);
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
  balancerEvents:
    ({ balancerEvents }, _dg, _rs, { 'balances/assetSymbol': assetSymbol }) =>
    (addresses): BalancerEvent[] => {
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
  balancerProfitLoss:
    ({ balancerEvents }, _dg, _rs, { 'balances/assetSymbol': assetSymbol }) =>
    addresses => {
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
              tokens: entry.poolTokens.map(token => token.token),
              profitLossAmount: entry.profitLossAmounts,
              usdProfitLoss: entry.usdProfitLoss
            };
          }
        }
      });
      return Object.values(balancerProfitLoss);
    }
};
