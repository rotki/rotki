import { AddressIndexed } from '@rotki/common';
import { DefiAccount } from '@rotki/common/lib/account';
import { Blockchain, DefiProtocol } from '@rotki/common/lib/blockchain';
import sortBy from 'lodash/sortBy';
import { ComputedRef, Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { balanceKeys } from '@/services/consts';
import { ProtocolVersion } from '@/services/defi/consts';
import { api } from '@/services/rotkehlchen-api';
import {
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES
} from '@/services/session/consts';
import { useAaveStore } from '@/store/defi/aave';
import { useBalancerStore } from '@/store/defi/balancer';
import { useCompoundStore } from '@/store/defi/compound';
import { useLiquityStore } from '@/store/defi/liquity';
import { useMakerDaoStore } from '@/store/defi/makerdao';
import { useDefiSupportedProtocolsStore } from '@/store/defi/protocols';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import {
  AllDefiProtocols,
  DefiProtocolSummary,
  TokenInfo
} from '@/store/defi/types';
import { useUniswapStore } from '@/store/defi/uniswap';
import { useYearnStore } from '@/store/defi/yearn';
import { useNotifications } from '@/store/notifications';
import { getStatus, setStatus } from '@/store/status';
import { useTasks } from '@/store/tasks';
import { isLoading } from '@/store/utils';
import { Writeable } from '@/types';
import {
  Airdrop,
  AIRDROP_POAP,
  AirdropDetail,
  Airdrops,
  AirdropType,
  PoapDelivery
} from '@/types/airdrops';
import {
  AAVE,
  COMPOUND,
  getProtocolIcon,
  LIQUITY,
  MAKERDAO_DSR,
  MAKERDAO_VAULTS,
  OverviewDefiProtocol,
  YEARN_FINANCE_VAULTS,
  YEARN_FINANCE_VAULTS_V2
} from '@/types/defi/protocols';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

type ResetStateParams =
  | Module
  | typeof ALL_MODULES
  | typeof ALL_DECENTRALIZED_EXCHANGES;
export const useDefiStore = defineStore('defi', () => {
  const allProtocols: Ref<AllDefiProtocols> = ref({});
  const airdrops: Ref<Airdrops> = ref({});

  const { awaitTask } = useTasks();
  const { notify } = useNotifications();
  const premium = usePremium();

  const liquityStore = useLiquityStore();
  const yearnStore = useYearnStore();
  const aaveStore = useAaveStore();
  const compoundStore = useCompoundStore();
  const makerDaoStore = useMakerDaoStore();
  const balancerStore = useBalancerStore();
  const sushiswapStore = useSushiswapStore();
  const uniswapStore = useUniswapStore();
  const lendingStore = useDefiSupportedProtocolsStore();
  const { t, tc } = useI18n();

  const {
    vaultsBalances: yearnV1Balances,
    vaultsHistory: yearnV1History,
    vaultsV2Balances: yearnV2Balances,
    vaultsV2History: yearnV2History
  } = storeToRefs(yearnStore);
  const { history: aaveHistory, balances: aaveBalances } =
    storeToRefs(aaveStore);
  const { history: compoundHistory, balances: compoundBalances } =
    storeToRefs(compoundStore);
  const { dsrHistory, dsrBalances } = storeToRefs(makerDaoStore);
  const airdropAddresses = computed(() => Object.keys(get(airdrops)));

  const airdropList = (addresses: string[]): ComputedRef<Airdrop[]> =>
    computed(() => {
      const result: Airdrop[] = [];
      const data = get(airdrops);
      for (const address in data) {
        if (addresses.length > 0 && !addresses.includes(address)) {
          continue;
        }
        const airdrop = data[address];
        for (const source in airdrop) {
          const element = airdrop[source as AirdropType];
          if (source === AIRDROP_POAP) {
            const details = element as PoapDelivery[];
            result.push({
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
            result.push({
              address,
              amount,
              link,
              source: source as AirdropType,
              asset
            });
          }
        }
      }
      return result;
    });

  const defiAccounts = (
    protocols: DefiProtocol[]
  ): ComputedRef<DefiAccount[]> =>
    computed(() => {
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
    });

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
        : get(lendingStore.loanSummary(filter));
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
          : get(lendingStore.totalLendingDeposit(filter, []))
      };
    };
    const summary: { [protocol: string]: Writeable<DefiProtocolSummary> } = {};

    const defiProtocols = get(allProtocols);
    for (const address of Object.keys(defiProtocols)) {
      const protocols = defiProtocols[address];
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
        totalLendingDepositUsd: get(
          lendingStore.totalLendingDeposit(filter, [])
        )
      };

      const { totalCollateralUsd, totalDebt } = get(
        lendingStore.loanSummary([DefiProtocol.MAKERDAO_VAULTS])
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

    return sortBy(Object.values(summary), 'protocol.name').filter(
      value => value.balanceUsd || value.deposits || value.liabilities
    );
  });

  const fetchDefiBalances = async (refresh: boolean) => {
    const section = Section.DEFI_BALANCES;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    setStatus(Status.LOADING, section);
    try {
      const taskType = TaskType.DEFI_BALANCES;
      const { taskId } = await api.defi.fetchAllDefi();
      const { result } = await awaitTask<AllDefiProtocols, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.balances.task.title'),
          numericKeys: balanceKeys
        }
      );

      set(allProtocols, result);
    } catch (e: any) {
      const title = tc('actions.defi.balances.error.title');
      const message = tc('actions.defi.balances.error.description', undefined, {
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

  async function fetchAllDefi(refresh: boolean = false) {
    const section = Section.DEFI_OVERVIEW;
    const currentStatus = getStatus(section);
    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);
    await fetchDefiBalances(refresh);
    setStatus(Status.PARTIALLY_LOADED, section);

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

    setStatus(Status.LOADED, section);
  }

  async function resetDB(protocols: DefiProtocol[]) {
    const premiumSection = Section.DEFI_LENDING_HISTORY;
    const currentPremiumStatus = getStatus(premiumSection);

    if (!get(premium) || isLoading(currentPremiumStatus)) {
      return;
    }

    setStatus(Status.REFRESHING, premiumSection);

    const toReset: Promise<void>[] = [];

    if (protocols.includes(DefiProtocol.YEARN_VAULTS)) {
      toReset.push(
        yearnStore.fetchHistory({
          refresh: true,
          reset: true,
          version: ProtocolVersion.V1
        })
      );
    }

    if (protocols.includes(DefiProtocol.YEARN_VAULTS_V2)) {
      toReset.push(
        yearnStore.fetchHistory({
          refresh: true,
          reset: true,
          version: ProtocolVersion.V2
        })
      );
    }

    if (protocols.includes(DefiProtocol.AAVE)) {
      toReset.push(aaveStore.fetchHistory({ refresh: true, reset: true }));
    }

    await Promise.all(toReset);

    setStatus(Status.LOADED, premiumSection);
  }

  async function fetchAirdrops(refresh: boolean = false) {
    const section = Section.DEFI_AIRDROPS;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const { taskId } = await api.defi.fetchAirdrops();
      const { result } = await awaitTask<Airdrops, TaskMeta>(
        taskId,
        TaskType.DEFI_AIRDROPS,
        {
          title: t('actions.defi.airdrops.task.title').toString(),
          numericKeys: balanceKeys
        }
      );
      set(airdrops, result);
    } catch (e: any) {
      notify({
        title: t('actions.defi.airdrops.error.title').toString(),
        message: t('actions.defi.airdrops.error.description', {
          error: e.message
        }).toString(),
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  }

  const modules: Record<string, Function> = {
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
    set(airdrops, {});
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
    airdrops,
    airdropAddresses,
    airdropList,
    defiAccounts,
    fetchDefiBalances,
    fetchAllDefi,
    fetchAirdrops,
    resetDB,
    resetState,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useDefiStore, import.meta.hot));
}
