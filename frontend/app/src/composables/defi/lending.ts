import { type Balance, BigNumber } from '@rotki/common';
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { assetSymbolToIdentifierMap } from '@rotki/common/lib/data';
import {
  type AaveHistoryTotal,
  type AaveLending
} from '@rotki/common/lib/defi/aave';
import sortBy from 'lodash/sortBy';
import {
  type AaveLoan,
  type BaseDefiBalance,
  type DefiBalance,
  type LoanSummary
} from '@/types/defi/lending';
import { type Writeable } from '@/types';
import { type Collateral, type DefiLoan, ProtocolVersion } from '@/types/defi';
import {
  type CompoundBalances,
  type CompoundLoan
} from '@/types/defi/compound';
import { type MakerDAOVaultModel } from '@/types/defi/maker';
import { type YearnVaultsHistory } from '@/types/defi/yearn';
import { Section, Status } from '@/types/status';
import { type LiquityLoan } from '@/types/defi/liquity';

type NullableLoan =
  | MakerDAOVaultModel
  | AaveLoan
  | CompoundLoan
  | LiquityLoan
  | null;

export const useDefiLending = () => {
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

  const { setStatus, fetchDisabled } = useStatusUpdater(Section.DEFI_LENDING);
  const { scrambleHex, scrambleIdentifier } = useScramble();

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
                label: scrambleIdentifier(value.identifier),
                protocol: DefiProtocol.MAKERDAO_VAULTS
              } satisfies DefiLoan)
          )
        );
      }

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
        const perAddressAaveBalances = get(aaveBalances);
        for (const address of Object.keys(perAddressAaveBalances)) {
          const { borrowing } = perAddressAaveBalances[address];
          const assets = Object.keys(borrowing);
          if (assets.length === 0) {
            continue;
          }

          for (const asset of assets) {
            const symbol = get(assetInfo(asset))?.symbol ?? asset;
            const formattedAddress = truncateAddress(scrambleHex(address), 6);

            loans.push({
              identifier: `${symbol} - ${address}`,
              label: `${symbol} - ${formattedAddress}`,
              protocol: DefiProtocol.AAVE,
              owner: address,
              asset
            });
          }
        }
      }

      if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
        const compBalances = get(compoundBalances);
        for (const address of Object.keys(compBalances)) {
          const { borrowing } = compBalances[address];
          const assets = Object.keys(borrowing);

          if (assets.length === 0) {
            continue;
          }

          for (const asset of assets) {
            const symbol = get(assetInfo(asset))?.symbol ?? asset;
            const formattedAddress = truncateAddress(scrambleHex(address), 6);

            loans.push({
              identifier: `${symbol} - ${address}`,
              label: `${symbol} - ${formattedAddress}`,
              protocol: DefiProtocol.COMPOUND,
              owner: address,
              asset
            });
          }
        }
      }

      if (showAll || protocols.includes(DefiProtocol.LIQUITY)) {
        const { balances } = useLiquityStore();
        const balanceAddress = Object.keys(balances);

        loans.push(
          ...balanceAddress.filter(uniqueStrings).map(address => {
            const troveId = balances[address] ? balances[address].troveId : 0;
            const formattedTroveId = scrambleIdentifier(troveId);
            const formattedAddress = truncateAddress(scrambleHex(address), 6);

            return {
              identifier: `Trove ${troveId} - ${address}`,
              label: `Trove ${formattedTroveId} - ${formattedAddress}`,
              protocol: DefiProtocol.LIQUITY,
              owner: address,
              asset: ''
            };
          })
        );
      }

      return sortBy(loans, 'identifier');
    });

  const loan = (identifier?: string): ComputedRef<NullableLoan> =>
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
        const makerVaults: MakerDAOVaultModel[] = get(makerDAOVaults);
        const vault = makerVaults.find(
          vault => vault.identifier.toString().toLocaleLowerCase() === id
        );

        if (!vault) {
          return null;
        }

        const makerVaultDetails = get(makerDAOVaultDetails);
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
        const perAddressAaveBalances = get(aaveBalances);
        const perAddressAaveHistory = get(aaveHistory);
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
        if (perAddressAaveHistory[owner]) {
          const { totalLost, totalEarnedLiquidations } =
            perAddressAaveHistory[owner];

          if (totalLost[asset]) {
            lost[asset] = totalLost[asset];
          }
          if (!liquidationEarned[asset] && totalEarnedLiquidations[asset]) {
            liquidationEarned[asset] = totalEarnedLiquidations[asset];
          }
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
          liquidationEarned
        } satisfies AaveLoan;
      }

      if (loan.protocol === DefiProtocol.COMPOUND) {
        const owner = loan.owner ?? '';
        const asset = loan.asset ?? '';

        let apy = '0%';
        let debt: Balance = zeroBalance();
        let collateral: Collateral[] = [];

        const compBalances = get(compoundBalances);
        if (compBalances[owner]) {
          const { borrowing, lending } = compBalances[owner];
          const selectedLoan = borrowing[asset];

          if (selectedLoan) {
            apy = selectedLoan.apy ?? '';
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
          collateral
        } satisfies CompoundLoan;
      }

      if (loan.protocol === DefiProtocol.LIQUITY) {
        assert(loan.owner);
        const { owner } = loan;
        const { balances } = useLiquityStore();

        return {
          owner,
          protocol: loan.protocol,
          balance: balances[owner]
        } satisfies LiquityLoan;
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
          .reduce(
            (sum: BigNumber, { collateral: { usdValue } }) =>
              sum.plus(usdValue),
            Zero
          )
          .plus(totalCollateralUsd);

        totalDebt = makerVaults
          .reduce((sum, { debt: { usdValue } }) => sum.plus(usdValue), Zero)
          .plus(totalDebt);
      }

      if (showAll || protocols.includes(DefiProtocol.AAVE)) {
        const perAddressAaveBalances = get(aaveBalances);
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
        const compBalances = get(compoundBalances);
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
        const makerDsrBalances = get(dsrBalances);
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
        const perAddressAaveBalances = get(aaveBalances);
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
        const compBalances: CompoundBalances = get(compoundBalances);
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

  const fetchLending = async (refresh = false): Promise<void> => {
    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

    if (!fetchDisabled(refresh)) {
      setStatus(newStatus);

      await Promise.allSettled([
        makerDaoStore.fetchDSRBalances(refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED);
        }),
        aaveStore.fetchBalances(refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED);
        }),
        compoundStore.fetchBalances(refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED);
        }),
        yearnStore
          .fetchBalances({
            refresh: refresh ?? false,
            version: ProtocolVersion.V1
          })
          .then(() => {
            setStatus(Status.PARTIALLY_LOADED);
          }),
        yearnStore
          .fetchBalances({
            refresh: refresh ?? false,
            version: ProtocolVersion.V2
          })
          .then(() => {
            setStatus(Status.PARTIALLY_LOADED);
          })
      ]);

      setStatus(Status.LOADED);
    }

    const isPremium = get(premium);
    const premiumSection = Section.DEFI_LENDING_HISTORY;
    if (!isPremium || fetchDisabled(refresh, premiumSection)) {
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
  };

  const fetchBorrowing = async (refresh = false): Promise<void> => {
    const section = Section.DEFI_BORROWING;
    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

    if (!fetchDisabled(refresh, section)) {
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

    const isPremium = get(premium);
    const premiumSection = Section.DEFI_BORROWING_HISTORY;

    if (!isPremium || fetchDisabled(refresh, premiumSection)) {
      return;
    }

    setStatus(newStatus, premiumSection);

    await Promise.all([
      makerDaoStore.fetchMakerDAOVaultDetails(refresh),
      compoundStore.fetchHistory(refresh),
      aaveStore.fetchHistory({ refresh })
    ]);

    setStatus(Status.LOADED, premiumSection);
  };

  const effectiveInterestRate = (
    protocols: DefiProtocol[],
    addresses: string[]
  ): ComputedRef<string> =>
    computed(() => {
      const lendBalances = get(lendingBalances(protocols, addresses));
      let { usdValue, weight } = lendBalances
        .filter(({ balance }) => balance.usdValue.gt(0))
        .map(({ effectiveInterestRate, balance: { usdValue } }) => {
          const n = Number.parseFloat(effectiveInterestRate);
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
            usdValue,
            weight: usdValue.multipliedBy(Number.parseFloat(roi))
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
        const history = get(dsrHistory);
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
        total = total.plus(yearnTotalEarned(get(yearnV1History)));
      }

      if (showAll || protocols.includes(DefiProtocol.YEARN_VAULTS_V2)) {
        total = total.plus(yearnTotalEarned(get(yearnV2History)));
      }
      return total;
    });

  const totalLendingDeposit = (
    protocols: DefiProtocol[],
    addresses: string[]
  ): ComputedRef<BigNumber> =>
    computed(() => {
      const lendBalances = get(lendingBalances(protocols, addresses));
      let lendingDeposit = balanceUsdValueSum(lendBalances);

      const getYearnDeposit = (
        version: ProtocolVersion = ProtocolVersion.V1
      ): BigNumber =>
        get(yearnStore.yearnVaultsAssets(addresses, version)).reduce(
          (sum, { underlyingValue: { usdValue } }) => sum.plus(usdValue),
          Zero
        );

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
        {} as Record<string, BaseDefiBalance[]>
      );

      const aggregated: BaseDefiBalance[] = [];

      for (const asset in balances) {
        const { weight, amount, usdValue } = balances[asset]
          .map(({ effectiveInterestRate, balance: { usdValue, amount } }) => ({
            weight: usdValue.multipliedBy(
              Number.parseFloat(effectiveInterestRate)
            ),
            usdValue,
            amount
          }))
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
    fetchLending,
    fetchBorrowing
  };
};
