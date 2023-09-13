//TODO: Split class
/* eslint-disable max-lines */
import { type DefiAccount } from '@rotki/common/lib/account';
import { Blockchain, DefiProtocol } from '@rotki/common/lib/blockchain';
import sortBy from 'lodash/sortBy';
import { type Writeable } from '@/types';
import {
  AllDefiProtocols,
  type DefiProtocolSummary,
  type TokenInfo
} from '@/types/defi/overview';
import {
  AAVE,
  COMPOUND,
  LIQUITY,
  MAKERDAO_DSR,
  MAKERDAO_VAULTS,
  type OverviewDefiProtocol,
  YEARN_FINANCE_VAULTS,
  YEARN_FINANCE_VAULTS_V2,
  getProtocolIcon
} from '@/types/defi/protocols';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { ProtocolVersion } from '@/types/defi';
import {
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES
} from '@/types/session/purge';

type ResetStateParams =
  | Module
  | typeof ALL_MODULES
  | typeof ALL_DECENTRALIZED_EXCHANGES;

export const useDefiStore = defineStore('defi', () => {
  const allProtocols: Ref<AllDefiProtocols> = ref({});

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const premium = usePremium();

  const liquityStore = useLiquityStore();
  const yearnStore = useYearnStore();
  const aaveStore = useAaveStore();
  const compoundStore = useCompoundStore();
  const makerDaoStore = useMakerDaoStore();
  const balancerStore = useBalancerStore();
  const sushiswapStore = useSushiswapStore();
  const uniswapStore = useUniswapStore();
  const { loanSummary, totalLendingDeposit } = useDefiLending();
  const { t } = useI18n();

  const { fetchAllDefi: fetchAllDefiCaller } = useDefiApi();

  const { addressesV1: yearnV1Addresses, addressesV2: yearnV2Addresses } =
    storeToRefs(yearnStore);
  const { addresses: aaveAddresses } = storeToRefs(aaveStore);
  const { addresses: compoundAddresses } = storeToRefs(compoundStore);
  const { addresses: makerDaoAddresses } = storeToRefs(makerDaoStore);

  type DefiProtocols = Exclude<
    DefiProtocol,
    DefiProtocol.MAKERDAO_VAULTS | DefiProtocol.UNISWAP | DefiProtocol.LIQUITY
  >;

  const defiAccounts = (
    protocols: DefiProtocol[]
  ): ComputedRef<DefiAccount[]> =>
    computed(() => {
      const addresses: {
        [key in DefiProtocols]: string[];
      } = {
        [DefiProtocol.MAKERDAO_DSR]: [],
        [DefiProtocol.AAVE]: [],
        [DefiProtocol.COMPOUND]: [],
        [DefiProtocol.YEARN_VAULTS]: [],
        [DefiProtocol.YEARN_VAULTS_V2]: []
      };

      if (
        protocols.length === 0 ||
        protocols.includes(DefiProtocol.MAKERDAO_DSR)
      ) {
        addresses[DefiProtocol.MAKERDAO_DSR] = get(makerDaoAddresses);
      }

      if (protocols.length === 0 || protocols.includes(DefiProtocol.AAVE)) {
        addresses[DefiProtocol.AAVE] = get(aaveAddresses);
      }

      if (protocols.length === 0 || protocols.includes(DefiProtocol.COMPOUND)) {
        addresses[DefiProtocol.COMPOUND] = get(compoundAddresses);
      }

      if (
        protocols.length === 0 ||
        protocols.includes(DefiProtocol.YEARN_VAULTS)
      ) {
        addresses[DefiProtocol.YEARN_VAULTS] = get(yearnV1Addresses);
      }

      if (
        protocols.length === 0 ||
        protocols.includes(DefiProtocol.YEARN_VAULTS_V2)
      ) {
        addresses[DefiProtocol.YEARN_VAULTS_V2] = get(yearnV2Addresses);
      }

      const accounts: Record<string, DefiAccount> = {};
      for (const protocol in addresses) {
        const selectedProtocol = protocol as DefiProtocols;
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
    });

  const { getStatus, setStatus, fetchDisabled } = useStatusUpdater(
    Section.DEFI_OVERVIEW
  );

  const overview: ComputedRef<DefiProtocolSummary[]> = computed(() => {
    const shouldDisplay = (summary: DefiProtocolSummary) => {
      const lending = summary.totalLendingDepositUsd.gt(0);
      const debt = summary.totalDebtUsd.gt(0);
      const balance = summary.balanceUsd && summary.balanceUsd.gt(0);
      const collateral = summary.totalCollateralUsd.gt(0);
      return lending || debt || balance || collateral;
    };

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
        : get(loanSummary(filter));
      return {
        protocol: {
          name,
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
          : get(totalLendingDeposit(filter, []))
      };
    };

    const summary: Record<string, DefiProtocolSummary> = {};

    const defiProtocols = get(allProtocols);
    for (const address of Object.keys(defiProtocols)) {
      const protocols = defiProtocols[address];
      for (const entry of protocols) {
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
        totalLendingDepositUsd: get(totalLendingDeposit(filter, []))
      };

      const { totalCollateralUsd, totalDebt } = get(
        loanSummary([DefiProtocol.MAKERDAO_VAULTS])
      );
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

    return sortBy(
      Object.values(summary),
      summary => summary.protocol.name
    ).filter(value => value.balanceUsd || value.deposits || value.liabilities);
  });

  const fetchDefiBalances = async (refresh: boolean) => {
    const section = Section.DEFI_BALANCES;

    if (fetchDisabled(refresh, section)) {
      return;
    }

    setStatus(Status.LOADING, section);
    try {
      const taskType = TaskType.DEFI_BALANCES;
      const { taskId } = await fetchAllDefiCaller();
      const { result } = await awaitTask<AllDefiProtocols, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.defi.balances.task.title')
        }
      );

      set(allProtocols, AllDefiProtocols.parse(result));
    } catch (e: any) {
      const title = t('actions.defi.balances.error.title');
      const message = t('actions.defi.balances.error.description', {
        error: e.message
      });
      notify({
        title,
        message,
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  };

  async function fetchAllDefi(refresh = false) {
    if (fetchDisabled(refresh)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);
    await fetchDefiBalances(refresh);
    setStatus(Status.PARTIALLY_LOADED);

    await Promise.allSettled([
      aaveStore.fetchBalances(refresh),
      makerDaoStore.fetchDSRBalances(refresh),
      makerDaoStore.fetchMakerDAOVaults(refresh),
      compoundStore.fetchBalances(refresh),
      yearnStore.fetchBalances({
        refresh,
        version: ProtocolVersion.V1
      }),
      yearnStore.fetchBalances({
        refresh,
        version: ProtocolVersion.V2
      }),
      liquityStore.fetchBalances(refresh)
    ]);

    setStatus(Status.LOADED);
  }

  const modules: Record<string, () => void> = {
    [Module.MAKERDAO_DSR]: () => makerDaoStore.reset(Module.MAKERDAO_DSR),
    [Module.MAKERDAO_VAULTS]: () => makerDaoStore.reset(Module.MAKERDAO_VAULTS),
    [Module.AAVE]: () => aaveStore.reset(),
    [Module.COMPOUND]: () => compoundStore.reset(),
    [Module.YEARN]: () => yearnStore.reset(ProtocolVersion.V1),
    [Module.YEARN_V2]: () => yearnStore.reset(ProtocolVersion.V2),
    [Module.UNISWAP]: () => uniswapStore.reset(),
    [Module.SUSHISWAP]: () => sushiswapStore.reset(),
    [Module.BALANCER]: () => balancerStore.reset(),
    [Module.LIQUITY]: () => liquityStore.reset()
  };

  const resetState = (module: ResetStateParams) => {
    if (module === ALL_DECENTRALIZED_EXCHANGES) {
      [Module.UNISWAP, Module.SUSHISWAP, Module.BALANCER].map(mod =>
        modules[mod]()
      );
    } else if (module === ALL_MODULES) {
      for (const mod in modules) {
        modules[mod as Module]();
      }
    } else {
      const reset = modules[module];

      if (!reset) {
        logger.warn(`Missing reset function for ${module}`);
      } else {
        reset();
      }
    }
  };

  const reset = () => {
    set(allProtocols, {});
    resetState(ALL_MODULES);
  };

  watch(premium, premium => {
    if (!premium) {
      reset();
    }
  });

  return {
    allProtocols,
    overview,
    defiAccounts,
    fetchDefiBalances,
    fetchAllDefi,
    resetState,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useDefiStore, import.meta.hot));
}
