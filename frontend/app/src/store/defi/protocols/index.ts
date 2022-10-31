import { Balance, BigNumber } from '@rotki/common';
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { assetSymbolToIdentifierMap } from '@rotki/common/lib/data';
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
import sortBy from 'lodash/sortBy';
import { ComputedRef } from 'vue';
import { usePremium } from '@/composables/premium';
import { truncateAddress } from '@/filters';
import { ProtocolVersion } from '@/services/defi/consts';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useAaveStore } from '@/store/defi/aave';
import { useCompoundStore } from '@/store/defi/compound';
import { useLiquityStore } from '@/store/defi/liquity';
import { LiquityLoan } from '@/store/defi/liquity/types';
import { useMakerDaoStore } from '@/store/defi/makerdao';
import {
  AaveLoan,
  BaseDefiBalance,
  DefiBalance,
  DefiLendingHistory,
  LoanSummary
} from '@/store/defi/types';
import { balanceUsdValueSum } from '@/store/defi/utils';
import { useYearnStore } from '@/store/defi/yearn';
import { getStatus, setStatus } from '@/store/status';
import { isLoading } from '@/store/utils';
import { Writeable } from '@/types';
import { Collateral, DefiLoan } from '@/types/defi';
import { CompoundBalances, CompoundLoan } from '@/types/defi/compound';
import {
  DSRBalances,
  DSRHistory,
  MakerDAOVaultDetails,
  MakerDAOVaultModel
} from '@/types/defi/maker';
import { YearnVaultsHistory } from '@/types/defi/yearn';
import { Section, Status } from '@/types/status';
import { assert } from '@/utils/assertions';
import { Zero, zeroBalance } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';

const isLendingEvent = (value: AaveHistoryEvents): value is AaveEvent => {
  const lending: string[] = Object.keys(AaveLendingEventType);
  return lending.indexOf(value.eventType) !== -1;
};
export const useDefiSupportedProtocolsStore = defineStore(
  'defi/supportedProtocols',
  () => {
    const { assetInfo } = useAssetInfoRetrieval();
    const premium = usePremium();

    const liquityStore = useLiquityStore();
    const yearnStore = useYearnStore();
    const aaveStore = useAaveStore();
    const compoundStore = useCompoundStore();
    const makerDaoStore = useMakerDaoStore();

    const { vaultsHistory: yearnV1History, vaultsV2History: yearnV2History } =
      storeToRefs(yearnStore);
    const { history: aaveHistory, balances: aaveBalances } =
      storeToRefs(aaveStore);
    const { history: compoundHistory, balances: compoundBalances } =
      storeToRefs(compoundStore);
    const { dsrHistory, dsrBalances, makerDAOVaults, makerDAOVaultDetails } =
      storeToRefs(makerDaoStore);
    const { balances: liquityBalances } = storeToRefs(liquityStore);

    const lendingHistory = (
      protocols: DefiProtocol[],
      addresses: string[]
    ): ComputedRef<DefiLendingHistory<DefiProtocol>[]> =>
      computed(() => {
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
                asset: assetSymbolToIdentifierMap.DAI,
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
      });

    const loans = (protocols: DefiProtocol[] = []): ComputedRef<DefiLoan[]> =>
      computed(() => {
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
            const borrowEvents: string[] = Object.values(
              AaveBorrowingEventType
            );
            const historyAssets = events
              .filter(e => borrowEvents.includes(e.eventType))
              .map(event =>
                isAaveLiquidationEvent(event)
                  ? event.principalAsset
                  : event.asset
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
                  identifier: `Trove ${troveId} - ${truncateAddress(
                    address,
                    6
                  )}`,
                  protocol: DefiProtocol.LIQUITY,
                  owner: address,
                  asset: ''
                };
              })
          );
        }

        return sortBy(loans, 'identifier');
      });

    const loan = (
      identifier?: string
    ): ComputedRef<
      MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan | null
    > =>
      computed(() => {
        const id = identifier?.toLocaleLowerCase();
        const allLoans = get(loans());
        const loan = allLoans.find(
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

          return details
            ? {
                ...vault,
                ...details,
                asset: assetSymbolToIdentifierMap.DAI
              }
            : vault;
        }

        if (loan.protocol === DefiProtocol.AAVE) {
          const perAddressAaveBalances = get(aaveBalances) as AaveBalances;
          const perAddressAaveHistory = get(aaveHistory) as AaveHistory;
          const owner = loan.owner ?? '';
          const asset = loan.asset ?? '';

          let selectedLoan = {
            stableApr: '-',
            variableApr: '-',
            balance: zeroBalance()
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
          let debt: Balance = zeroBalance();
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
              .filter(
                ({ eventType }) => !['mint', 'redeem'].includes(eventType)
              )
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
      });

    const loanSummary = (
      protocols: DefiProtocol[] = []
    ): ComputedRef<LoanSummary> =>
      computed(() => {
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
            totalCollateralUsd = balanceUsdValueSum(
              Object.values(lending)
            ).plus(totalCollateralUsd);

            totalDebt = balanceUsdValueSum(Object.values(borrowing)).plus(
              totalDebt
            );
          }
        }

        if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
          const compBalances = get(compoundBalances) as CompoundBalances;
          for (const address of Object.keys(compBalances)) {
            const { borrowing, lending } = compBalances[address];
            totalCollateralUsd = balanceUsdValueSum(
              Object.values(lending)
            ).plus(totalCollateralUsd);

            totalDebt = balanceUsdValueSum(Object.values(borrowing)).plus(
              totalDebt
            );
          }
        }

        if (showAll || protocols.includes(DefiProtocol.LIQUITY)) {
          const balances = get(liquityBalances);
          for (const address in balances) {
            const balance = balances[address];
            const { collateral, debt } = balance;
            totalCollateralUsd = collateral.usdValue.plus(totalCollateralUsd);
            totalDebt = debt.usdValue.plus(totalDebt);
          }
        }

        return { totalCollateralUsd, totalDebt };
      });

    const lendingBalances = (
      protocols: DefiProtocol[],
      addresses: string[]
    ): ComputedRef<DefiBalance[]> =>
      computed(() => {
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
              asset: assetSymbolToIdentifierMap.DAI,
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
      });

    async function fetchLending(refresh: boolean = false) {
      const isPremium = get(premium);
      const section = Section.DEFI_LENDING;
      const premiumSection = Section.DEFI_LENDING_HISTORY;
      const currentStatus = getStatus(section);

      const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

      if (
        !isLoading(currentStatus) ||
        (currentStatus === Status.LOADED && refresh)
      ) {
        setStatus(newStatus, section);

        await Promise.allSettled([
          makerDaoStore.fetchDSRBalances(refresh).then(() => {
            setStatus(Status.PARTIALLY_LOADED, section);
          }),
          aaveStore.fetchBalances(refresh).then(() => {
            setStatus(Status.PARTIALLY_LOADED, section);
          }),
          compoundStore.fetchBalances(refresh).then(() => {
            setStatus(Status.PARTIALLY_LOADED, section);
          }),
          yearnStore
            .fetchBalances({
              refresh: refresh ?? false,
              version: ProtocolVersion.V1
            })
            .then(() => {
              setStatus(Status.PARTIALLY_LOADED, section);
            }),
          yearnStore
            .fetchBalances({
              refresh: refresh ?? false,
              version: ProtocolVersion.V2
            })
            .then(() => {
              setStatus(Status.PARTIALLY_LOADED, section);
            })
        ]);

        setStatus(Status.LOADED, section);
      }

      const currentPremiumStatus = getStatus(premiumSection);

      if (
        !isPremium ||
        isLoading(currentPremiumStatus) ||
        (currentPremiumStatus === Status.LOADED && !refresh)
      ) {
        return;
      }

      setStatus(newStatus, premiumSection);

      await Promise.all([
        makerDaoStore.fetchDSRHistory(refresh),
        aaveStore.fetchHistory({ refresh }),
        compoundStore.fetchHistory(refresh),
        yearnStore.fetchHistory({
          refresh: refresh ?? false,
          version: ProtocolVersion.V1
        }),
        yearnStore.fetchHistory({
          refresh: refresh ?? false,
          version: ProtocolVersion.V2
        })
      ]);

      setStatus(Status.LOADED, premiumSection);
    }

    async function fetchBorrowing(refresh: boolean = false) {
      const section = Section.DEFI_BORROWING;
      const premiumSection = Section.DEFI_BORROWING_HISTORY;
      const currentStatus = getStatus(section);
      const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

      if (
        !isLoading(currentStatus) ||
        (currentStatus === Status.LOADED && refresh)
      ) {
        setStatus(newStatus, section);
        await Promise.all([
          makerDaoStore.fetchMakerDAOVaults(refresh).then(() => {
            setStatus(Status.PARTIALLY_LOADED, section);
          }),
          compoundStore.fetchBalances(refresh).then(() => {
            setStatus(Status.PARTIALLY_LOADED, section);
          }),
          aaveStore.fetchBalances(refresh).then(() => {
            setStatus(Status.PARTIALLY_LOADED, section);
          }),
          liquityStore.fetchBalances(refresh).then(() => {
            setStatus(Status.PARTIALLY_LOADED, section);
          })
        ]);

        setStatus(Status.LOADED, section);
      }

      const currentPremiumStatus = getStatus(premiumSection);

      if (
        !get(premium) ||
        isLoading(currentPremiumStatus) ||
        (currentPremiumStatus === Status.LOADED && !refresh)
      ) {
        return;
      }

      setStatus(newStatus, premiumSection);

      await Promise.all([
        makerDaoStore.fetchMakerDAOVaultDetails(refresh),
        compoundStore.fetchHistory(refresh),
        aaveStore.fetchHistory({ refresh }),
        liquityStore.fetchEvents(refresh)
      ]);

      setStatus(Status.LOADED, premiumSection);
    }

    const effectiveInterestRate = (
      protocols: DefiProtocol[],
      addresses: string[]
    ): ComputedRef<string> =>
      computed(() => {
        const lendBalances = get(lendingBalances(protocols, addresses));
        let { usdValue, weight } = lendBalances
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
          return get(yearnStore.yearnVaultsAssets([], version))
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
      });

    const totalUsdEarned = (
      protocols: DefiProtocol[],
      addresses: string[]
    ): ComputedRef<BigNumber> =>
      computed(() => {
        let total = Zero;
        const showAll = protocols.length === 0;
        const allAddresses = addresses.length === 0;

        if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
          const history = get(dsrHistory) as DSRHistory;
          for (const address of Object.keys(history)) {
            if (!allAddresses && !addresses.includes(address)) {
              continue;
            }
            total = total.plus(history[address].gainSoFar.usdValue);
          }
        }

        if (showAll || protocols.includes(DefiProtocol.AAVE)) {
          const history = get(aaveHistory);
          for (const address of Object.keys(history)) {
            if (!allAddresses && !addresses.includes(address)) {
              continue;
            }
            const totalEarned = history[address].totalEarnedInterest;
            for (const asset of Object.keys(totalEarned)) {
              total = total.plus(totalEarned[asset].usdValue);
            }
          }
        }

        if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
          const history = get(compoundHistory);
          for (const address in history.interestProfit) {
            if (!allAddresses && !addresses.includes(address)) {
              continue;
            }

            const accountProfit = history.interestProfit[address];
            for (const asset in accountProfit) {
              const assetProfit = accountProfit[asset];
              total = total.plus(assetProfit.usdValue);
            }
          }
        }

        function yearnTotalEarned(
          vaultsHistory: YearnVaultsHistory
        ): BigNumber {
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
      });

    const totalLendingDeposit = (
      protocols: DefiProtocol[],
      addresses: string[]
    ): ComputedRef<BigNumber> =>
      computed(() => {
        const lendBalances = get(lendingBalances(protocols, addresses));
        let lendingDeposit = lendBalances
          .map(value => value.balance.usdValue)
          .reduce((sum, usdValue) => sum.plus(usdValue), Zero);

        function getYearnDeposit(
          version: ProtocolVersion = ProtocolVersion.V1
        ) {
          return get(yearnStore.yearnVaultsAssets(addresses, version))
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
      });

    const aggregatedLendingBalances = (
      protocols: DefiProtocol[],
      addresses: string[]
    ): ComputedRef<BaseDefiBalance[]> =>
      computed(() => {
        const lendBalances = get(lendingBalances(protocols, addresses));
        const balances = lendBalances.reduce(
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
                weight: usdValue.multipliedBy(
                  parseFloat(effectiveInterestRate)
                ),
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
      });

    return {
      effectiveInterestRate,
      totalLendingDeposit,
      totalUsdEarned,
      aggregatedLendingBalances,
      loan,
      loans,
      loanSummary,
      lendingBalances,
      lendingHistory,
      fetchLending,
      fetchBorrowing
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useDefiSupportedProtocolsStore, import.meta.hot)
  );
}
