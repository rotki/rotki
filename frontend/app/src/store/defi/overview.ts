import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';
import { sortBy } from 'lodash-es';
import {
  type DefiProtocolSummary,
  type TokenInfo
} from '@/types/defi/overview';
import { Section, Status } from '@/types/status';
import { type Writeable } from '@/types';

export const useDefiOverviewStore = defineStore('defi/store', () => {
  const { getStatus } = useStatusUpdater(Section.DEFI_OVERVIEW);

  const { loanSummary, totalLendingDeposit } = useDefiLending();

  const { allProtocols } = storeToRefs(useDefiStore());
  const { t } = useI18n();

  const { getDefiIdentifierByName } = useDefiMetadata();

  const shouldShowOverview = (summary: DefiProtocolSummary) => {
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
    noDeposits?: boolean
  ): ComputedRef<DefiProtocolSummary | undefined> =>
    computed(() => {
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
        : get(loanSummary(filter));

      return {
        protocol,
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
          : get(totalLendingDeposit(filter, []))
      };
    });

  const listedProtocols: Record<string, [Section, boolean, boolean]> = {
    [DefiProtocol.AAVE]: [Section.DEFI_AAVE_BALANCES, false, false],
    [DefiProtocol.COMPOUND]: [Section.DEFI_COMPOUND_BALANCES, false, false],
    [DefiProtocol.YEARN_VAULTS]: [
      Section.DEFI_YEARN_VAULTS_BALANCES,
      true,
      false
    ],
    [DefiProtocol.LIQUITY]: [Section.DEFI_LIQUITY_BALANCES, false, true]
  };

  const isListedDefiProtocol = (protocol: string): protocol is DefiProtocol =>
    Object.values(DefiProtocol).includes(protocol as any);

  const overview: ComputedRef<DefiProtocolSummary[]> = computed(() => {
    const summary: Record<string, DefiProtocolSummary> = {};

    const defiProtocols = get(allProtocols);
    for (const address of Object.keys(defiProtocols)) {
      const protocols = defiProtocols[address];
      for (const entry of protocols) {
        const protocol = entry.protocol.name;
        const protocolId = get(getDefiIdentifierByName(protocol));

        const data = listedProtocols[protocolId];
        if (data && isListedDefiProtocol(protocolId)) {
          const dataSummary = get(protocolSummary(protocolId, ...data));

          if (dataSummary && shouldShowOverview(dataSummary)) {
            summary[protocol] = dataSummary;
          }
          continue;
        }

        if (!summary[protocol]) {
          summary[protocol] = {
            protocol: protocolId,
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
          tokenInfo.tokenName = `${t('defi_overview.multiple_assets')}`;
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

    const overviewStatus = getStatus();
    if (
      overviewStatus === Status.LOADED ||
      overviewStatus === Status.REFRESHING
    ) {
      const filter: DefiProtocol[] = [DefiProtocol.MAKERDAO_DSR];
      const makerDAODSRSummary: DefiProtocolSummary = {
        protocol: DefiProtocol.MAKERDAO_DSR,
        tokenInfo: null,
        assets: [],
        depositsUrl: '/defi/deposits?protocol=makerdao',
        deposits: true,
        liabilities: false,
        totalCollateralUsd: Zero,
        totalDebtUsd: Zero,
        totalLendingDepositUsd: get(totalLendingDeposit(filter, []))
      };

      const { totalCollateralUsd, totalDebt } = get(
        loanSummary([DefiProtocol.MAKERDAO_VAULTS])
      );
      const makerDAOVaultSummary: DefiProtocolSummary = {
        protocol: DefiProtocol.MAKERDAO_VAULTS,
        tokenInfo: null,
        assets: [],
        deposits: false,
        liabilities: true,
        liabilitiesUrl: '/defi/liabilities?protocol=makerdao',
        totalDebtUsd: totalDebt,
        totalCollateralUsd,
        totalLendingDepositUsd: Zero
      };

      if (shouldShowOverview(makerDAODSRSummary)) {
        summary[DefiProtocol.MAKERDAO_DSR] = makerDAODSRSummary;
      }

      if (shouldShowOverview(makerDAOVaultSummary)) {
        summary[DefiProtocol.MAKERDAO_VAULTS] = makerDAOVaultSummary;
      }

      const yearnV2Summary = get(
        protocolSummary(
          DefiProtocol.YEARN_VAULTS_V2,
          Section.DEFI_YEARN_VAULTS_V2_BALANCES,
          true
        )
      );

      if (yearnV2Summary && shouldShowOverview(yearnV2Summary)) {
        summary[DefiProtocol.YEARN_VAULTS_V2] = yearnV2Summary;
      }
    }

    return sortBy(Object.values(summary), summary => summary.protocol).filter(
      value => value.balanceUsd || value.deposits || value.liabilities
    );
  });

  return {
    overview
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useDefiOverviewStore, import.meta.hot)
  );
}
