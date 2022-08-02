import { AddressIndexed, Balance, BigNumber } from '@rotki/common';
import { DefiAccount } from '@rotki/common/lib/account';
import { Blockchain, DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  AaveBalances,
  AaveBorrowingEventType,
  AaveEvent,
  AaveHistory,
  AaveHistoryEvents,
  AaveHistoryTotal,
  AaveLending,
  AaveLendingEventType,
  isAaveLiquidationEvent
} from '@rotki/common/lib/defi/aave';
import { DexTrade } from '@rotki/common/lib/defi/dex';
import { get } from '@vueuse/core';
import sortBy from 'lodash/sortBy';
import { storeToRefs } from 'pinia';
import { truncateAddress } from '@/filters';
import i18n from '@/i18n';
import { ProtocolVersion } from '@/services/defi/consts';
import { CompoundBalances, CompoundLoan } from '@/services/defi/types/compound';
import { YearnVaultsHistory } from '@/services/defi/types/yearn';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section, Status } from '@/store/const';
import { useAaveStore } from '@/store/defi/aave';
import { useBalancerStore } from '@/store/defi/balancer';
import { useCompoundStore } from '@/store/defi/compound';
import {
  AAVE,
  AIRDROP_POAP,
  COMPOUND,
  getProtocolIcon,
  LIQUITY,
  MAKERDAO_DSR,
  MAKERDAO_VAULTS,
  YEARN_FINANCE_VAULTS,
  YEARN_FINANCE_VAULTS_V2
} from '@/store/defi/const';
import { useLiquityStore } from '@/store/defi/liquity';
import { LiquityLoan } from '@/store/defi/liquity/types';
import { useMakerDaoStore } from '@/store/defi/makerdao';
import { useSushiswapStore } from '@/store/defi/sushiswap';
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
  DSRBalances,
  DSRHistory,
  LoanSummary,
  MakerDAOVaultDetails,
  MakerDAOVaultModel,
  OverviewDefiProtocol,
  PoapDelivery,
  TokenInfo
} from '@/store/defi/types';
import { useUniswap } from '@/store/defi/uniswap';
import { balanceUsdValueSum } from '@/store/defi/utils';
import { useYearnStore } from '@/store/defi/yearn';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { getStatus } from '@/store/utils';
import { Writeable } from '@/types';
import { assert } from '@/utils/assertions';
import { Zero } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';

function isLendingEvent(value: AaveHistoryEvents): value is AaveEvent {
  const lending: string[] = Object.keys(AaveLendingEventType);
  return lending.indexOf(value.eventType) !== -1;
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
  dexTrades: (addresses: string[]) => DexTrade[];
  airdrops: (addresses: string[]) => Airdrop[];
  airdropAddresses: string[];
}

export const getters: Getters<DefiState, DefiGetters, RotkehlchenState, any> = {
  totalUsdEarned:
    _ =>
    (protocols: DefiProtocol[], addresses: string[]): BigNumber => {
      const { vaultsHistory: yearnV1History, vaultsV2History: yearnV2History } =
        storeToRefs(useYearnStore());
      const { history } = storeToRefs(useAaveStore());
      const { history: compHistory } = storeToRefs(useCompoundStore());
      const { dsrHistory: dsrHistoryRef } = storeToRefs(useMakerDaoStore());
      const aaveHistory = get(history);
      const compoundHistory = get(compHistory);

      let total = Zero;
      const showAll = protocols.length === 0;
      const allAddresses = addresses.length === 0;

      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
        const dsrHistory = get(dsrHistoryRef) as DSRHistory;
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
        total = total.plus(
          yearnTotalEarned(get(yearnV1History) as YearnVaultsHistory)
        );
      }

      if (showAll || protocols.includes(DefiProtocol.YEARN_VAULTS_V2)) {
        total = total.plus(
          yearnTotalEarned(get(yearnV2History) as YearnVaultsHistory)
        );
      }
      return total;
    },

  defiAccounts:
    _ =>
    (protocols: DefiProtocol[]): DefiAccount[] => {
      const {
        vaultsBalances: yearnV1Balances,
        vaultsHistory: yearnV1History,
        vaultsV2Balances: yearnV2Balances,
        vaultsV2History: yearnV2History
      } = storeToRefs(useYearnStore());
      const { history: aaveHistory, balances: aaveBalances } = storeToRefs(
        useAaveStore()
      );
      const { history: compoundHistory, balances: compoundBalances } =
        storeToRefs(useCompoundStore());

      const { dsrHistory, dsrBalances } = storeToRefs(useMakerDaoStore());

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
        get(aaveBalances),
        get(aaveHistory)
      );

      addresses[DefiProtocol.COMPOUND] = getProtocolAddresses(
        DefiProtocol.COMPOUND,
        get(compoundBalances),
        get(compoundHistory).events.map(({ address }) => address)
      );

      addresses[DefiProtocol.YEARN_VAULTS] = getProtocolAddresses(
        DefiProtocol.YEARN_VAULTS,
        get(yearnV1Balances),
        get(yearnV1History)
      );

      addresses[DefiProtocol.YEARN_VAULTS_V2] = getProtocolAddresses(
        DefiProtocol.YEARN_VAULTS_V2,
        get(yearnV2Balances),
        get(yearnV2History)
      );

      addresses[DefiProtocol.MAKERDAO_DSR] = getProtocolAddresses(
        DefiProtocol.MAKERDAO_DSR,
        get(dsrBalances).balances,
        get(dsrHistory)
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
    _ =>
    (protocols: DefiProtocol[]): DefiLoan[] => {
      const { assetInfo } = useAssetInfoRetrieval();
      const { history: aaveHistory, balances: aaveBalances } = storeToRefs(
        useAaveStore()
      );
      const { history: compoundHistory, balances: compoundBalances } =
        storeToRefs(useCompoundStore());
      const { makerDAOVaults } = storeToRefs(useMakerDaoStore());

      const loans: DefiLoan[] = [];
      const showAll = protocols.length === 0;

      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_VAULTS)) {
        loans.push(
          ...get(makerDAOVaults).map(
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
        const perAddressAaveBalances = get(aaveBalances);
        for (const address of Object.keys(perAddressAaveBalances)) {
          const { borrowing } = perAddressAaveBalances[address];
          const assets = Object.keys(borrowing);
          if (assets.length === 0) {
            continue;
          }

          for (const asset of assets) {
            const symbol = get(assetInfo(asset))?.symbol ?? asset;
            loans.push({
              identifier: `${symbol} - ${truncateAddress(address, 6)}`,
              protocol: DefiProtocol.AAVE,
              owner: address,
              asset
            });
            knownAssets.push(asset);
          }
        }

        const perAddressAaveHistory = get(aaveHistory) as AaveHistory;
        for (const address in perAddressAaveHistory) {
          const { events } = perAddressAaveHistory[address];
          const borrowEvents: string[] = Object.values(AaveBorrowingEventType);
          const historyAssets = events
            .filter(e => borrowEvents.includes(e.eventType))
            .map(event =>
              isAaveLiquidationEvent(event) ? event.principalAsset : event.asset
            )
            .filter(uniqueStrings)
            .filter(asset => !knownAssets.includes(asset));

          for (const asset of historyAssets) {
            const symbol = get(assetInfo(asset))?.symbol ?? asset;
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
        const assetAddressPair = get(compoundHistory)
          .events.filter(
            ({ eventType }) => !['mint', 'redeem', 'comp'].includes(eventType)
          )
          .map(({ asset, address }) => ({ asset, address }));

        const compBalances = get(compoundBalances);
        for (const address of Object.keys(compBalances)) {
          const { borrowing } = compBalances[address];
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
        const { events, balances } = useLiquityStore();
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
    (_, { loans }) =>
    (
      identifier?: string
    ): MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan | null => {
      const { history: aaveHistory, balances: aaveBalances } = storeToRefs(
        useAaveStore()
      );
      const { history: compoundHistory, balances: compoundBalances } =
        storeToRefs(useCompoundStore());
      const { makerDAOVaults, makerDAOVaultDetails } = storeToRefs(
        useMakerDaoStore()
      );
      const id = identifier?.toLocaleLowerCase();
      const loan = loans([]).find(
        loan => loan.identifier.toLocaleLowerCase() === id
      );

      if (!loan) {
        return null;
      }

      if (loan.protocol === DefiProtocol.MAKERDAO_VAULTS) {
        const makerVaults = get(makerDAOVaults) as MakerDAOVaultModel[];
        const vault = makerVaults.find(
          vault => vault.identifier.toString().toLocaleLowerCase() === id
        );

        if (!vault) {
          return null;
        }

        const makerVaultDetails = get(
          makerDAOVaultDetails
        ) as MakerDAOVaultDetails[];
        const details = makerVaultDetails.find(
          details => details.identifier.toString().toLocaleLowerCase() === id
        );

        return details ? { ...vault, ...details, asset: 'DAI' } : vault;
      }

      if (loan.protocol === DefiProtocol.AAVE) {
        const perAddressAaveBalances = get(aaveBalances) as AaveBalances;
        const perAddressAaveHistory = get(aaveHistory) as AaveHistory;
        const owner = loan.owner ?? '';
        const asset = loan.asset ?? '';

        let selectedLoan = {
          stableApr: '-',
          variableApr: '-',
          balance: { amount: Zero, usdValue: Zero }
        };

        let lending: AaveLending = {};
        if (perAddressAaveBalances[owner]) {
          const balances = perAddressAaveBalances[owner];
          selectedLoan = balances.borrowing[asset] ?? selectedLoan;
          lending = balances.lending ?? lending;
        }

        const lost: Writeable<AaveHistoryTotal> = {};
        const liquidationEarned: Writeable<AaveHistoryTotal> = {};
        const events: AaveHistoryEvents[] = [];
        if (perAddressAaveHistory[owner]) {
          const {
            totalLost,
            events: allEvents,
            totalEarnedLiquidations
          } = perAddressAaveHistory[owner];

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

        const compBalances = get(compoundBalances) as CompoundBalances;
        if (compBalances[owner]) {
          const { borrowing, lending } = compBalances[owner];
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
          events: get(compoundHistory)
            .events.filter(
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
        assert(loan.owner);
        const { owner } = loan;
        const { balances, events } = useLiquityStore();

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
    _ =>
    (protocols: DefiProtocol[]): LoanSummary => {
      const { balances: aaveBalances } = storeToRefs(useAaveStore());
      const { balances: compoundBalances } = storeToRefs(useCompoundStore());
      const { makerDAOVaults } = storeToRefs(useMakerDaoStore());
      let totalCollateralUsd = Zero;
      let totalDebt = Zero;

      const showAll = protocols.length === 0;
      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_VAULTS)) {
        const makerVaults = get(makerDAOVaults);
        totalCollateralUsd = makerVaults
          .map(({ collateral: { usdValue } }) => usdValue)
          .reduce(
            (sum, collateralUsdValue) => sum.plus(collateralUsdValue),
            Zero
          )
          .plus(totalCollateralUsd);

        totalDebt = makerVaults
          .map(({ debt: { usdValue } }) => usdValue)
          .reduce((sum, debt) => sum.plus(debt), Zero)
          .plus(totalDebt);
      }

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
        const perAddressAaveBalances = get(aaveBalances) as AaveBalances;
        for (const address of Object.keys(perAddressAaveBalances)) {
          const { borrowing, lending } = perAddressAaveBalances[address];
          totalCollateralUsd = balanceUsdValueSum(Object.values(lending)).plus(
            totalCollateralUsd
          );

          totalDebt = balanceUsdValueSum(Object.values(borrowing)).plus(
            totalDebt
          );
        }
      }

      if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
        const compBalances = get(compoundBalances) as CompoundBalances;
        for (const address of Object.keys(compBalances)) {
          const { borrowing, lending } = compBalances[address];
          totalCollateralUsd = balanceUsdValueSum(Object.values(lending)).plus(
            totalCollateralUsd
          );

          totalDebt = balanceUsdValueSum(Object.values(borrowing)).plus(
            totalDebt
          );
        }
      }

      if (showAll || protocols.includes(DefiProtocol.LIQUITY)) {
        const { balances } = useLiquityStore();
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
    (_, { lendingBalances }) =>
    (protocols: DefiProtocol[], addresses: string[]): string => {
      const { yearnVaultsAssets } = useYearnStore();
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
        return get(yearnVaultsAssets([], version))
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
    (_: DefiState, { lendingBalances }) =>
    (protocols: DefiProtocol[], addresses: string[]): BigNumber => {
      const { yearnVaultsAssets } = useYearnStore();
      let lendingDeposit = lendingBalances(protocols, addresses)
        .map(value => value.balance.usdValue)
        .reduce((sum, usdValue) => sum.plus(usdValue), Zero);

      function getYearnDeposit(version: ProtocolVersion = ProtocolVersion.V1) {
        return get(yearnVaultsAssets(addresses, version))
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
    _ =>
    (protocols: DefiProtocol[], addresses: string[]): DefiBalance[] => {
      const { getAssetIdentifierForSymbol } = useAssetInfoRetrieval();
      const { balances: aaveBalances } = storeToRefs(useAaveStore());
      const { balances: compoundBalances } = storeToRefs(useCompoundStore());
      const { dsrBalances } = storeToRefs(useMakerDaoStore());

      const balances: DefiBalance[] = [];
      const showAll = protocols.length === 0;
      const allAddresses = addresses.length === 0;

      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
        const makerDsrBalances = get(dsrBalances) as DSRBalances;
        for (const address of Object.keys(makerDsrBalances.balances)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }
          const balance = makerDsrBalances.balances[address];
          const currentDsr = makerDsrBalances.currentDsr;
          // noinspection SuspiciousTypeOfGuard
          const isBigNumber = currentDsr instanceof BigNumber;
          const format = isBigNumber ? currentDsr.toFormat(2) : 0;
          balances.push({
            address,
            protocol: DefiProtocol.MAKERDAO_DSR,
            asset: getAssetIdentifierForSymbol('DAI'),
            balance: { ...balance },
            effectiveInterestRate: `${format}%`
          });
        }
      }

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
        const perAddressAaveBalances = get(aaveBalances) as AaveBalances;
        for (const address of Object.keys(perAddressAaveBalances)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }
          const { lending } = perAddressAaveBalances[address];

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
        const compBalances = get(compoundBalances) as CompoundBalances;
        for (const address of Object.keys(compBalances)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }
          const { lending } = compBalances[address];
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
    _ =>
    (
      protocols: DefiProtocol[],
      addresses: string[]
    ): DefiLendingHistory<DefiProtocol>[] => {
      const { vaultsHistory: yearnV1History, vaultsV2History: yearnV2History } =
        storeToRefs(useYearnStore());
      const { history: aaveHistory } = storeToRefs(useAaveStore());
      const { history: compoundHistory } = storeToRefs(useCompoundStore());
      const { dsrHistory } = storeToRefs(useMakerDaoStore());
      const { getAssetIdentifierForSymbol } = useAssetInfoRetrieval();

      const defiLendingHistory: DefiLendingHistory<DefiProtocol>[] = [];
      const showAll = protocols.length === 0;
      const allAddresses = addresses.length === 0;
      let id = 1;

      if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
        const makerDsrHistory = get(dsrHistory) as DSRHistory;
        for (const address of Object.keys(makerDsrHistory)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }

          const history = makerDsrHistory[address];

          for (const movement of history.movements) {
            defiLendingHistory.push({
              id: `${movement.txHash}-${id++}`,
              eventType: movement.movementType,
              protocol: DefiProtocol.MAKERDAO_DSR,
              address,
              asset: getAssetIdentifierForSymbol('DAI'),
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
        const perAddressAaveHistory = get(aaveHistory) as AaveHistory;
        for (const address of Object.keys(perAddressAaveHistory)) {
          if (!allAddresses && !addresses.includes(address)) {
            continue;
          }

          const history = perAddressAaveHistory[address];

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
        for (const event of get(compoundHistory).events) {
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
        const vaultsHistory = get(isV1 ? yearnV1History : yearnV2History);
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

  defiOverview: ({ allProtocols }, { loanSummary, totalLendingDeposit }, _) => {
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
      const currentStatus = getStatus(section);
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
          icon: getProtocolIcon(name)
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
              icon: getProtocolIcon(protocol)
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

    const overviewStatus = getStatus(Section.DEFI_OVERVIEW);
    if (
      overviewStatus === Status.LOADED ||
      overviewStatus === Status.REFRESHING
    ) {
      const filter: DefiProtocol[] = [DefiProtocol.MAKERDAO_DSR];
      const makerDAODSRSummary: DefiProtocolSummary = {
        protocol: {
          name: MAKERDAO_DSR,
          icon: getProtocolIcon(MAKERDAO_DSR)
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
          icon: getProtocolIcon(MAKERDAO_VAULTS)
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

  dexTrades:
    () =>
    (addresses): DexTrade[] => {
      const { trades: uniswapTrades } = useUniswap();
      const { trades: sushiswapTrades } = useSushiswapStore();
      const { trades: balancerTrades } = useBalancerStore();
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
      addTrades(uniswapTrades as DexTrades, addresses, trades);
      addTrades(balancerTrades as DexTrades, addresses, trades);
      if (sushiswapTrades) {
        addTrades(sushiswapTrades as DexTrades, addresses, trades);
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
  airdropAddresses: ({ airdrops }) => Object.keys(airdrops)
};
