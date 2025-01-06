// TODO: Split class
/* eslint-disable max-lines */
import { type AaveHistoryTotal, type AaveLending, type Balance, BigNumber, type Writeable, assetSymbolToIdentifierMap } from '@rotki/common';
import { sortBy } from 'es-toolkit';
import { type Collateral, type DefiLoan, ProtocolVersion } from '@/types/defi';
import { Section, Status } from '@/types/status';
import { DefiProtocol } from '@/types/modules';
import { balanceUsdValueSum, sum } from '@/utils/balances';
import { zeroBalance } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';
import { truncateAddress } from '@/utils/truncate';
import { useCompoundStore } from '@/store/defi/compound';
import { useMakerDaoStore } from '@/store/defi/makerdao';
import { useAaveStore } from '@/store/defi/aave';
import { useYearnStore } from '@/store/defi/yearn';
import { useLiquityStore } from '@/store/defi/liquity';
import { useStatusUpdater } from '@/composables/status';
import { useScramble } from '@/composables/scramble';
import { usePremium } from '@/composables/premium';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import type { AaveLoan, BaseDefiBalance, DefiBalance, LoanSummary } from '@/types/defi/lending';
import type { CompoundBalances, CompoundLoan } from '@/types/defi/compound';
import type { MakerDAOVaultModel } from '@/types/defi/maker';
import type { LiquityLoan } from '@/types/defi/liquity';
import type { ComputedRef } from 'vue';

type NullableLoan = MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan | null;

interface UseDefiLendingReturn {
  effectiveInterestRate: (protocols: DefiProtocol[], addresses: string[]) => ComputedRef<string>;
  totalLendingDeposit: (protocols: DefiProtocol[], addresses: string[]) => ComputedRef<BigNumber>;
  totalUsdEarned: (protocols: DefiProtocol[], addresses: string[]) => ComputedRef<BigNumber>;
  aggregatedLendingBalances: (protocols: DefiProtocol[], addresses: string[]) => ComputedRef<BaseDefiBalance[]>;
  loan: (identifier?: string) => ComputedRef<NullableLoan>;
  loans: (protocols?: DefiProtocol[]) => ComputedRef<DefiLoan[]>;
  loanSummary: (protocols?: DefiProtocol[]) => ComputedRef<LoanSummary>;
  lendingBalances: (protocols: DefiProtocol[], addresses: string[]) => ComputedRef<DefiBalance[]>;
  fetchLending: (refresh?: boolean) => Promise<void>;
  fetchBorrowing: (refresh?: boolean) => Promise<void>;
}

export function useDefiLending(): UseDefiLendingReturn {
  const { assetInfo } = useAssetInfoRetrieval();
  const premium = usePremium();

  const liquityStore = useLiquityStore();
  const yearnStore = useYearnStore();
  const aaveStore = useAaveStore();
  const compoundStore = useCompoundStore();
  const makerDaoStore = useMakerDaoStore();

  const { balances: aaveBalances, history: aaveHistory } = storeToRefs(aaveStore);
  const { balances: compoundBalances, history: compoundHistory } = storeToRefs(compoundStore);
  const { dsrBalances, dsrHistory, makerDAOVaultDetails, makerDAOVaults } = storeToRefs(makerDaoStore);
  const { balances: liquityBalances } = storeToRefs(liquityStore);

  const { fetchDisabled, setStatus } = useStatusUpdater(Section.DEFI_LENDING);
  const { scrambleAddress, scrambleIdentifier } = useScramble();

  const { yearnVaultsAssets } = yearnStore;

  const loans = (protocols: DefiProtocol[] = []): ComputedRef<DefiLoan[]> => computed<DefiLoan[]>(() => {
    const loans: DefiLoan[] = [];
    const showAll = protocols.length === 0;

    if (showAll || protocols.includes(DefiProtocol.MAKERDAO_VAULTS)) {
      loans.push(...get(makerDAOVaults).map(value => ({
        identifier: `${value.identifier}`,
        label: scrambleIdentifier(value.identifier),
        protocol: DefiProtocol.MAKERDAO_VAULTS,
      }) satisfies DefiLoan));
    }

    if (showAll || protocols.includes(DefiProtocol.AAVE)) {
      const perAddressAaveBalances = get(aaveBalances);
      for (const address of Object.keys(perAddressAaveBalances)) {
        const { borrowing } = perAddressAaveBalances[address];
        const assets = Object.keys(borrowing);
        if (assets.length === 0)
          continue;

        for (const asset of assets) {
          const symbol = get(assetInfo(asset))?.symbol ?? asset;
          const formattedAddress = truncateAddress(scrambleAddress(address), 6);

          loans.push({
            asset,
            identifier: `${symbol} - ${address}`,
            label: `${symbol} - ${formattedAddress}`,
            owner: address,
            protocol: DefiProtocol.AAVE,
          });
        }
      }
    }

    if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
      const compBalances = get(compoundBalances);
      for (const address of Object.keys(compBalances)) {
        const { borrowing } = compBalances[address];
        const assets = Object.keys(borrowing);

        if (assets.length === 0)
          continue;

        for (const asset of assets) {
          const symbol = get(assetInfo(asset))?.symbol ?? asset;
          const formattedAddress = truncateAddress(scrambleAddress(address), 6);

          loans.push({
            asset,
            identifier: `${symbol} - ${address}`,
            label: `${symbol} - ${formattedAddress}`,
            owner: address,
            protocol: DefiProtocol.COMPOUND,
          });
        }
      }
    }

    if (showAll || protocols.includes(DefiProtocol.LIQUITY)) {
      const { balances } = get(liquityBalances);
      const balanceAddress = Object.keys(balances);

      loans.push(
        ...balanceAddress.filter(uniqueStrings).map((address) => {
          const troveId = balances[address] ? balances[address].troveId : 0;
          const formattedTroveId = scrambleIdentifier(troveId);
          const formattedAddress = truncateAddress(scrambleAddress(address), 6);

          return {
            asset: '',
            identifier: `Trove ${troveId} - ${address}`,
            label: `Trove ${formattedTroveId} - ${formattedAddress}`,
            owner: address,
            protocol: DefiProtocol.LIQUITY,
          };
        }),
      );
    }

    return sortBy(loans, ['identifier']);
  });

  const loan = (identifier?: string): ComputedRef<NullableLoan> => computed<NullableLoan>(() => {
    const id = identifier?.toLocaleLowerCase();
    const allLoans = get(loans());
    const loan = allLoans.find(loan => loan.identifier.toLocaleLowerCase() === id);

    if (!loan)
      return null;

    if (loan.protocol === DefiProtocol.MAKERDAO_VAULTS) {
      const makerVaults: MakerDAOVaultModel[] = get(makerDAOVaults);
      const vault = makerVaults.find(vault => vault.identifier.toString().toLocaleLowerCase() === id);

      if (!vault)
        return null;

      const makerVaultDetails = get(makerDAOVaultDetails);
      const details = makerVaultDetails.find(details => details.identifier.toString().toLocaleLowerCase() === id);

      return details
        ? {
            ...vault,
            ...details,
            asset: assetSymbolToIdentifierMap.DAI,
          }
        : vault;
    }

    if (loan.protocol === DefiProtocol.AAVE) {
      const perAddressAaveBalances = get(aaveBalances);
      const perAddressAaveHistory = get(aaveHistory);
      const owner = loan.owner ?? '';
      const asset = loan.asset ?? '';

      let selectedLoan = {
        balance: zeroBalance(),
        stableApr: '-',
        variableApr: '-',
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
        const { totalEarnedLiquidations, totalLost } = perAddressAaveHistory[owner];

        if (totalLost[asset])
          lost[asset] = totalLost[asset];

        if (!liquidationEarned[asset] && totalEarnedLiquidations[asset])
          liquidationEarned[asset] = totalEarnedLiquidations[asset];
      }

      return {
        asset,
        collateral: Object.keys(lending).map(asset => ({
          asset,
          ...lending[asset].balance,
        })),
        debt: {
          amount: selectedLoan.balance.amount,
          usdValue: selectedLoan.balance.usdValue,
        },
        identifier: loan.identifier,
        liquidationEarned,
        owner,
        protocol: loan.protocol,
        stableApr: selectedLoan.stableApr,
        totalLost: lost,
        variableApr: selectedLoan.variableApr,
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
            ...lending[asset].balance,
          }));
        }
      }

      return {
        apy,
        asset,
        collateral,
        debt,
        identifier: loan.identifier,
        owner,
        protocol: loan.protocol,
      } satisfies CompoundLoan;
    }

    if (loan.protocol === DefiProtocol.LIQUITY) {
      assert(loan.owner);
      const { owner } = loan;

      return {
        balance: get(liquityBalances).balances[owner],
        owner,
        protocol: loan.protocol,
      } satisfies LiquityLoan;
    }

    return null;
  });

  const loanSummary = (protocols: DefiProtocol[] = []): ComputedRef<LoanSummary> => computed<LoanSummary>(() => {
    let totalCollateralUsd = Zero;
    let totalDebt = Zero;

    const showAll = protocols.length === 0;
    if (showAll || protocols.includes(DefiProtocol.MAKERDAO_VAULTS)) {
      const makerVaults = get(makerDAOVaults);
      totalCollateralUsd = makerVaults
        .reduce((sum: BigNumber, { collateral: { usdValue } }) => sum.plus(usdValue), Zero)
        .plus(totalCollateralUsd);

      totalDebt = makerVaults.reduce((sum, { debt: { usdValue } }) => sum.plus(usdValue), Zero).plus(totalDebt);
    }

    if (showAll || protocols.includes(DefiProtocol.AAVE)) {
      const perAddressAaveBalances = get(aaveBalances);
      for (const address of Object.keys(perAddressAaveBalances)) {
        const { borrowing, lending } = perAddressAaveBalances[address];
        totalCollateralUsd = balanceUsdValueSum(Object.values(lending)).plus(totalCollateralUsd);

        totalDebt = balanceUsdValueSum(Object.values(borrowing)).plus(totalDebt);
      }
    }

    if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
      const compBalances = get(compoundBalances);
      for (const address of Object.keys(compBalances)) {
        const { borrowing, lending } = compBalances[address];
        totalCollateralUsd = balanceUsdValueSum(Object.values(lending)).plus(totalCollateralUsd);

        totalDebt = balanceUsdValueSum(Object.values(borrowing)).plus(totalDebt);
      }
    }

    if (showAll || protocols.includes(DefiProtocol.LIQUITY)) {
      const { balances } = get(liquityBalances);
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
    addresses: string[],
  ): ComputedRef<DefiBalance[]> => computed<DefiBalance[]>(() => {
    const balances: DefiBalance[] = [];
    const showAll = protocols.length === 0;
    const allAddresses = addresses.length === 0;

    if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
      const makerDsrBalances = get(dsrBalances);
      for (const address of Object.keys(makerDsrBalances.balances)) {
        if (!allAddresses && !addresses.includes(address))
          continue;

        const balance = makerDsrBalances.balances[address];
        const currentDsr = makerDsrBalances.currentDsr;
        // noinspection SuspiciousTypeOfGuard
        const isBigNumber = currentDsr instanceof BigNumber;
        const format = isBigNumber ? currentDsr.toFormat(2) : 0;
        balances.push({
          address,
          asset: assetSymbolToIdentifierMap.DAI,
          effectiveInterestRate: `${format}%`,
          protocol: DefiProtocol.MAKERDAO_DSR,
          ...balance,
        });
      }
    }

    if (showAll || protocols.includes(DefiProtocol.AAVE)) {
      const perAddressAaveBalances = get(aaveBalances);
      for (const address of Object.keys(perAddressAaveBalances)) {
        if (!allAddresses && !addresses.includes(address))
          continue;

        const { lending } = perAddressAaveBalances[address];

        for (const asset of Object.keys(lending)) {
          const aaveAsset = lending[asset];
          balances.push({
            address,
            asset,
            effectiveInterestRate: aaveAsset.apy,
            protocol: DefiProtocol.AAVE,
            ...aaveAsset.balance,
          });
        }
      }
    }

    if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
      const compBalances: CompoundBalances = get(compoundBalances);
      for (const address of Object.keys(compBalances)) {
        if (!allAddresses && !addresses.includes(address))
          continue;

        const { lending } = compBalances[address];
        for (const asset of Object.keys(lending)) {
          const assetDetails = lending[asset];
          balances.push({
            address,
            asset,
            effectiveInterestRate: assetDetails.apy ?? '0%',
            protocol: DefiProtocol.COMPOUND,
            ...assetDetails.balance,
          });
        }
      }
    }

    return sortBy(balances, ['asset']);
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
            version: ProtocolVersion.V1,
          })
          .then(() => {
            setStatus(Status.PARTIALLY_LOADED);
          }),
        yearnStore
          .fetchBalances({
            refresh: refresh ?? false,
            version: ProtocolVersion.V2,
          })
          .then(() => {
            setStatus(Status.PARTIALLY_LOADED);
          }),
      ]);

      setStatus(Status.LOADED);
    }

    const isPremium = get(premium);
    const premiumSection = { section: Section.DEFI_LENDING_HISTORY };
    if (!isPremium || fetchDisabled(refresh, premiumSection))
      return;

    setStatus(newStatus, premiumSection);

    await Promise.all([
      makerDaoStore.fetchDSRHistory(refresh),
      aaveStore.fetchHistory({ refresh }),
      compoundStore.fetchStats(refresh),
    ]);

    setStatus(Status.LOADED, premiumSection);
  };

  const fetchBorrowing = async (refresh = false): Promise<void> => {
    const section = { section: Section.DEFI_BORROWING };
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
        }),
      ]);

      setStatus(Status.LOADED, section);
    }

    const isPremium = get(premium);
    const premiumSection = { section: Section.DEFI_BORROWING_HISTORY };

    if (!isPremium || fetchDisabled(refresh, premiumSection))
      return;

    setStatus(newStatus, premiumSection);

    await Promise.all([
      makerDaoStore.fetchMakerDAOVaultDetails(refresh),
      compoundStore.fetchStats(refresh),
      aaveStore.fetchHistory({ refresh }),
    ]);

    setStatus(Status.LOADED, premiumSection);
  };

  const effectiveInterestRate = (
    protocols: DefiProtocol[],
    addresses: string[],
  ): ComputedRef<string> => computed<string>(() => {
    const lendBalances = get(lendingBalances(protocols, addresses));
    let { usdValue, weight } = lendBalances
      .filter(({ usdValue }) => usdValue.gt(0))
      .map(({ effectiveInterestRate, usdValue }) => {
        const n = Number.parseFloat(effectiveInterestRate);
        return {
          usdValue,
          weight: usdValue.multipliedBy(n),
        };
      })
      .reduce(
        (sum, current) => ({
          usdValue: sum.usdValue.plus(current.usdValue),
          weight: sum.weight.plus(current.weight),
        }),
        {
          usdValue: Zero,
          weight: Zero,
        },
      );

    const yearnData = (
      version: ProtocolVersion,
    ): ComputedRef<{
      weight: BigNumber;
      usdValue: BigNumber;
    }> =>
      computed(() => {
        const filtered: {
          weight: BigNumber;
          usdValue: BigNumber;
        }[] = [];

        get(yearnVaultsAssets(addresses, version)).forEach(({ roi, underlyingValue: { usdValue } }) => {
          if (roi && usdValue.gt(Zero)) {
            filtered.push({
              usdValue,
              weight: usdValue.multipliedBy(Number.parseFloat(roi)),
            });
          }
        });

        return filtered.reduce(
          ({ usdValue, weight: sWeight }, current) => ({
            usdValue: usdValue.plus(current.usdValue),
            weight: sWeight.plus(current.weight),
          }),
          { usdValue: Zero, weight: Zero },
        );
      });

    if (protocols.length === 0 || protocols.includes(DefiProtocol.YEARN_VAULTS)) {
      const { usdValue: yUsdValue, weight: yWeight } = get(yearnData(ProtocolVersion.V1));
      usdValue = usdValue.plus(yUsdValue);
      weight = weight.plus(yWeight);
    }

    if (protocols.length === 0 || protocols.includes(DefiProtocol.YEARN_VAULTS_V2)) {
      const { usdValue: yUsdValue, weight: yWeight } = get(yearnData(ProtocolVersion.V2));
      usdValue = usdValue.plus(yUsdValue);
      weight = weight.plus(yWeight);
    }

    const effectiveInterestRate = weight.div(usdValue);
    return effectiveInterestRate.isNaN() ? '0.00%' : `${effectiveInterestRate.toFormat(2)}%`;
  });

  const totalUsdEarned = (
    protocols: DefiProtocol[],
    addresses: string[],
  ): ComputedRef<BigNumber> => computed<BigNumber>(() => {
    let total = Zero;
    const showAll = protocols.length === 0;
    const allAddresses = addresses.length === 0;

    if (showAll || protocols.includes(DefiProtocol.MAKERDAO_DSR)) {
      const history = get(dsrHistory);
      for (const address of Object.keys(history)) {
        if (!allAddresses && !addresses.includes(address))
          continue;

        total = total.plus(history[address].gainSoFar.usdValue);
      }
    }

    if (showAll || protocols.includes(DefiProtocol.AAVE)) {
      const history = get(aaveHistory);
      for (const address of Object.keys(history)) {
        if (!allAddresses && !addresses.includes(address))
          continue;

        const totalEarned = history[address].totalEarnedInterest;
        for (const asset of Object.keys(totalEarned)) total = total.plus(totalEarned[asset].usdValue);
      }
    }

    if (showAll || protocols.includes(DefiProtocol.COMPOUND)) {
      const history = get(compoundHistory);
      for (const address in history.interestProfit) {
        if (!allAddresses && !addresses.includes(address))
          continue;

        const accountProfit = history.interestProfit[address];
        for (const asset in accountProfit) {
          const assetProfit = accountProfit[asset];
          total = total.plus(assetProfit.usdValue);
        }
      }
    }

    return total;
  });

  const totalLendingDeposit = (
    protocols: DefiProtocol[],
    addresses: string[],
  ): ComputedRef<BigNumber> => computed<BigNumber>(() => {
    const lendBalances = get(lendingBalances(protocols, addresses));
    let lendingDeposit = sum(lendBalances);

    const getYearnDeposit = (version: ProtocolVersion): ComputedRef<BigNumber> => computed<BigNumber>(() =>
      get(yearnVaultsAssets(addresses, version)).reduce(
        (sum, { underlyingValue: { usdValue } }) => sum.plus(usdValue),
        Zero,
      ));

    if (protocols.length === 0 || protocols.includes(DefiProtocol.YEARN_VAULTS))
      lendingDeposit = lendingDeposit.plus(get(getYearnDeposit(ProtocolVersion.V1)));

    if (protocols.length === 0 || protocols.includes(DefiProtocol.YEARN_VAULTS_V2))
      lendingDeposit = lendingDeposit.plus(get(getYearnDeposit(ProtocolVersion.V2)));

    return lendingDeposit;
  });

  const aggregatedLendingBalances = (
    protocols: DefiProtocol[],
    addresses: string[],
  ): ComputedRef<BaseDefiBalance[]> => computed<BaseDefiBalance[]>(() => {
    const lendBalances = get(lendingBalances(protocols, addresses));

    const balances = lendBalances.reduce(
      (grouped, { address, protocol, ...baseBalance }) => {
        const { asset } = baseBalance;
        if (!grouped[asset])
          grouped[asset] = [baseBalance];
        else grouped[asset].push(baseBalance);

        return grouped;
      },
      {} as Record<string, BaseDefiBalance[]>,
    );

    const aggregated: BaseDefiBalance[] = [];

    for (const asset in balances) {
      const { amount, usdValue, weight } = balances[asset]
        .map(({ amount, effectiveInterestRate, usdValue }) => ({
          amount,
          usdValue,
          weight: usdValue.multipliedBy(Number.parseFloat(effectiveInterestRate)),
        }))
        .reduce(
          (sum, current) => ({
            amount: sum.amount.plus(current.amount),
            usdValue: sum.usdValue.plus(current.usdValue),
            weight: sum.weight.plus(current.weight),
          }),
          {
            amount: Zero,
            usdValue: Zero,
            weight: Zero,
          },
        );

      const effectiveInterestRate = weight.div(usdValue);

      aggregated.push({
        amount,
        asset,
        effectiveInterestRate: effectiveInterestRate.isNaN() ? '0.00%' : `${effectiveInterestRate.toFormat(2)}%`,
        usdValue,
      });
    }
    return aggregated;
  });

  return {
    aggregatedLendingBalances,
    effectiveInterestRate,
    fetchBorrowing,
    fetchLending,
    lendingBalances,
    loan,
    loans,
    loanSummary,
    totalLendingDeposit,
    totalUsdEarned,
  };
}
