import { sortBy } from 'es-toolkit';
import { Section, Status } from '@/types/status';
import { DefiProtocol, isDefiProtocol } from '@/types/modules';
import { useDefiStore } from '@/store/defi/index';
import { useDefiLending } from '@/composables/defi/lending';
import { useDefiMetadata } from '@/composables/defi/metadata';
import { useStatusUpdater } from '@/composables/status';
import type { DefiProtocolSummary } from '@/types/defi/overview';

export const useDefiOverviewStore = defineStore('defi/store', () => {
  const { getStatus } = useStatusUpdater(Section.DEFI_OVERVIEW);

  const { loanSummary, totalLendingDeposit } = useDefiLending();

  const { allProtocols } = storeToRefs(useDefiStore());
  const { t } = useI18n();

  const { getDefiIdentifierByName } = useDefiMetadata();

  const shouldShowOverview = (summary: DefiProtocolSummary): boolean => {
    const lending = summary.totalLendingDepositUsd.gt(0);
    const debt = summary.totalDebtUsd.gt(0);
    const balance = summary.balanceUsd && summary.balanceUsd.gt(0);
    const collateral = summary.totalCollateralUsd.gt(0);
    return lending || debt || balance || collateral;
  };

  const protocolSummary = (
    protocol: DefiProtocol,
    section: Section,
    noLiabilities?: boolean,
    noDeposits?: boolean,
  ): ComputedRef<DefiProtocolSummary | undefined> =>
    computed(() => {
      const currentStatus = getStatus({ section });
      if (currentStatus !== Status.LOADED && currentStatus !== Status.REFRESHING)
        return undefined;

      const filter: DefiProtocol[] = [protocol];
      const { totalCollateralUsd, totalDebt } = noLiabilities
        ? { totalCollateralUsd: Zero, totalDebt: Zero }
        : get(loanSummary(filter));

      return {
        assets: [],
        deposits: !noDeposits,
        depositsUrl: noDeposits ? undefined : `/defi/deposits?protocol=${protocol}`,
        liabilities: !noLiabilities,
        liabilitiesUrl: noLiabilities ? undefined : `/defi/liabilities?protocol=${protocol}`,
        protocol,
        tokenInfo: null,
        totalCollateralUsd,
        totalDebtUsd: totalDebt,
        totalLendingDepositUsd: noDeposits ? Zero : get(totalLendingDeposit(filter, [])),
      };
    });

  const listedProtocols: Record<string, [Section, boolean, boolean]> = {
    [DefiProtocol.AAVE]: [Section.DEFI_AAVE_BALANCES, false, false],
    [DefiProtocol.COMPOUND]: [Section.DEFI_COMPOUND_BALANCES, false, false],
    [DefiProtocol.LIQUITY]: [Section.DEFI_LIQUITY_BALANCES, false, true],
    [DefiProtocol.YEARN_VAULTS]: [Section.DEFI_YEARN_VAULTS_BALANCES, true, false],
  };

  const overview = computed<DefiProtocolSummary[]>(() => {
    const summary: Record<string, DefiProtocolSummary> = {};

    const defiProtocols = get(allProtocols);
    for (const address of Object.keys(defiProtocols)) {
      const protocols = defiProtocols[address];
      for (const entry of protocols) {
        const protocol = entry.protocol.name;
        const protocolId = get(getDefiIdentifierByName(protocol));

        const data = listedProtocols[protocolId];
        if (data && isDefiProtocol(protocolId)) {
          const dataSummary = get(protocolSummary(protocolId, ...data));

          if (dataSummary && shouldShowOverview(dataSummary))
            summary[protocol] = dataSummary;

          continue;
        }

        if (!summary[protocol]) {
          summary[protocol] = {
            assets: [],
            deposits: false,
            liabilities: false,
            protocol: protocolId,
            tokenInfo: {
              tokenName: entry.baseBalance.tokenName,
              tokenSymbol: entry.baseBalance.tokenSymbol,
            },
            totalCollateralUsd: Zero,
            totalDebtUsd: Zero,
            totalLendingDepositUsd: Zero,
          };
        }
        else if (summary[protocol].tokenInfo?.tokenName !== entry.baseBalance.tokenName) {
          summary[protocol].tokenInfo = {
            tokenName: `${t('defi_overview.multiple_assets')}`,
            tokenSymbol: '',
          };
        }

        const { balance } = entry.baseBalance;
        if (entry.balanceType === 'Asset') {
          const previousBalance = summary[protocol].balanceUsd ?? Zero;
          summary[protocol].balanceUsd = previousBalance.plus(balance.usdValue);
          const assetIndex = summary[protocol].assets.findIndex(
            asset => asset.tokenAddress === entry.baseBalance.tokenAddress,
          );
          if (assetIndex >= 0) {
            const { amount, usdValue } = entry.baseBalance.balance;
            const asset = summary[protocol].assets[assetIndex];
            const usdValueSum = usdValue.plus(asset.balance.usdValue);
            const amountSum = amount.plus(asset.balance.amount);

            summary[protocol].assets[assetIndex] = {
              ...asset,
              balance: {
                amount: amountSum,
                usdValue: usdValueSum,
              },
            };
          }
          else {
            summary[protocol].assets.push(entry.baseBalance);
          }
        }
      }
    }

    const overviewStatus = getStatus();
    if (overviewStatus === Status.LOADED || overviewStatus === Status.REFRESHING) {
      const filter: DefiProtocol[] = [DefiProtocol.MAKERDAO_DSR];
      const makerDAODSRSummary: DefiProtocolSummary = {
        assets: [],
        deposits: true,
        depositsUrl: '/defi/deposits?protocol=makerdao',
        liabilities: false,
        protocol: DefiProtocol.MAKERDAO_DSR,
        tokenInfo: null,
        totalCollateralUsd: Zero,
        totalDebtUsd: Zero,
        totalLendingDepositUsd: get(totalLendingDeposit(filter, [])),
      };

      const { totalCollateralUsd, totalDebt } = get(loanSummary([DefiProtocol.MAKERDAO_VAULTS]));
      const makerDAOVaultSummary: DefiProtocolSummary = {
        assets: [],
        deposits: false,
        liabilities: true,
        liabilitiesUrl: '/defi/liabilities?protocol=makerdao',
        protocol: DefiProtocol.MAKERDAO_VAULTS,
        tokenInfo: null,
        totalCollateralUsd,
        totalDebtUsd: totalDebt,
        totalLendingDepositUsd: Zero,
      };

      if (shouldShowOverview(makerDAODSRSummary))
        summary[DefiProtocol.MAKERDAO_DSR] = makerDAODSRSummary;

      if (shouldShowOverview(makerDAOVaultSummary))
        summary[DefiProtocol.MAKERDAO_VAULTS] = makerDAOVaultSummary;

      const yearnV2Summary = get(
        protocolSummary(DefiProtocol.YEARN_VAULTS_V2, Section.DEFI_YEARN_VAULTS_V2_BALANCES, true),
      );

      if (yearnV2Summary && shouldShowOverview(yearnV2Summary))
        summary[DefiProtocol.YEARN_VAULTS_V2] = yearnV2Summary;
    }

    return sortBy(Object.values(summary), ['protocol']).filter(
      value => value.balanceUsd || value.deposits || value.liabilities,
    );
  });

  return {
    overview,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useDefiOverviewStore, import.meta.hot));
