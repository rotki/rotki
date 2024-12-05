import { Blockchain } from '@rotki/common';
import { AllDefiProtocols } from '@/types/defi/overview';
import { DECENTRALIZED_EXCHANGES, DefiProtocol, Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { type DefiAccount, ProtocolVersion } from '@/types/defi';
import { Purgeable } from '@/types/session/purge';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useUniswapStore } from '@/store/defi/uniswap';
import { useMakerDaoStore } from '@/store/defi/makerdao';
import { useCompoundStore } from '@/store/defi/compound';
import { useAaveStore } from '@/store/defi/aave';
import { useYearnStore } from '@/store/defi/yearn';
import { useLiquityStore } from '@/store/defi/liquity';
import { useDefiApi } from '@/composables/api/defi';
import { useStatusUpdater } from '@/composables/status';
import { usePremium } from '@/composables/premium';
import type { TaskMeta } from '@/types/task';

type ResetStateParams = Module | typeof Purgeable.DEFI_MODULES | typeof Purgeable.DECENTRALIZED_EXCHANGES;

export const useDefiStore = defineStore('defi', () => {
  const allProtocols = ref<AllDefiProtocols>({});

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const premium = usePremium();

  const liquityStore = useLiquityStore();
  const yearnStore = useYearnStore();
  const aaveStore = useAaveStore();
  const compoundStore = useCompoundStore();
  const makerDaoStore = useMakerDaoStore();
  const sushiswapStore = useSushiswapStore();
  const uniswapStore = useUniswapStore();
  const { t } = useI18n();

  const { fetchAllDefi: fetchAllDefiCaller } = useDefiApi();

  const { addressesV1: yearnV1Addresses, addressesV2: yearnV2Addresses } = storeToRefs(yearnStore);
  const { addresses: aaveAddresses } = storeToRefs(aaveStore);
  const { addresses: compoundAddresses } = storeToRefs(compoundStore);
  const { addresses: makerDaoAddresses } = storeToRefs(makerDaoStore);

  type DefiProtocols = Exclude<
    DefiProtocol,
    DefiProtocol.MAKERDAO_VAULTS | DefiProtocol.UNISWAP | DefiProtocol.LIQUITY
  >;

  const defiAccounts = (protocols: DefiProtocol[]): ComputedRef<DefiAccount[]> => computed<DefiAccount[]>(() => {
    const addresses: {
      [key in DefiProtocols]: string[];
    } = {
      [DefiProtocol.AAVE]: [],
      [DefiProtocol.COMPOUND]: [],
      [DefiProtocol.MAKERDAO_DSR]: [],
      [DefiProtocol.YEARN_VAULTS]: [],
      [DefiProtocol.YEARN_VAULTS_V2]: [],
    };

    const noProtocolsSelected = protocols.length === 0;

    if (noProtocolsSelected || protocols.includes(DefiProtocol.MAKERDAO_DSR))
      addresses[DefiProtocol.MAKERDAO_DSR] = get(makerDaoAddresses);

    if (noProtocolsSelected || protocols.includes(DefiProtocol.AAVE))
      addresses[DefiProtocol.AAVE] = get(aaveAddresses);

    if (noProtocolsSelected || protocols.includes(DefiProtocol.COMPOUND))
      addresses[DefiProtocol.COMPOUND] = get(compoundAddresses);

    if (noProtocolsSelected || protocols.includes(DefiProtocol.YEARN_VAULTS))
      addresses[DefiProtocol.YEARN_VAULTS] = get(yearnV1Addresses);

    if (noProtocolsSelected || protocols.includes(DefiProtocol.YEARN_VAULTS_V2))
      addresses[DefiProtocol.YEARN_VAULTS_V2] = get(yearnV2Addresses);

    const accounts: Record<string, DefiAccount> = {};
    for (const protocol in addresses) {
      const selectedProtocol = protocol as DefiProtocols;
      const perProtocolAddresses = addresses[selectedProtocol];
      for (const address of perProtocolAddresses) {
        if (accounts[address]) {
          accounts[address].protocols.push(selectedProtocol);
        }
        else {
          accounts[address] = {
            chain: Blockchain.ETH,
            data: {
              address,
              type: 'address',
            },
            nativeAsset: Blockchain.ETH.toUpperCase(),
            protocols: [selectedProtocol],
          };
        }
      }
    }

    return Object.values(accounts);
  });

  const { fetchDisabled, setStatus } = useStatusUpdater(Section.DEFI_BALANCES);

  const fetchDefiBalances = async (refresh: boolean): Promise<void> => {
    if (fetchDisabled(refresh))
      return;

    setStatus(Status.LOADING);
    try {
      const taskType = TaskType.DEFI_BALANCES;
      const { taskId } = await fetchAllDefiCaller();
      const { result } = await awaitTask<AllDefiProtocols, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.balances.task.title'),
      });

      set(allProtocols, AllDefiProtocols.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const title = t('actions.defi.balances.error.title');
        const message = t('actions.defi.balances.error.description', {
          error: error.message,
        });
        notify({
          display: true,
          message,
          title,
        });
      }
    }
    setStatus(Status.LOADED);
  };

  async function fetchAllDefi(refresh = false): Promise<void> {
    const section = { section: Section.DEFI_OVERVIEW };

    if (fetchDisabled(refresh, section))
      return;

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
        version: ProtocolVersion.V1,
      }),
      yearnStore.fetchBalances({
        refresh,
        version: ProtocolVersion.V2,
      }),
      liquityStore.fetchBalances(refresh),
    ]);

    setStatus(Status.LOADED, section);
  }

  const modules: Record<string, () => void> = {
    [Module.AAVE]: () => aaveStore.reset(),
    [Module.COMPOUND]: () => compoundStore.reset(),
    [Module.LIQUITY]: () => liquityStore.reset(),
    [Module.MAKERDAO_DSR]: () => makerDaoStore.reset(Module.MAKERDAO_DSR),
    [Module.MAKERDAO_VAULTS]: () => makerDaoStore.reset(Module.MAKERDAO_VAULTS),
    [Module.SUSHISWAP]: () => sushiswapStore.reset(),
    [Module.UNISWAP]: () => uniswapStore.reset(),
    [Module.YEARN]: () => yearnStore.reset(ProtocolVersion.V1),
    [Module.YEARN_V2]: () => yearnStore.reset(ProtocolVersion.V2),
  };

  const resetState = (module: ResetStateParams): void => {
    if (module === Purgeable.DECENTRALIZED_EXCHANGES) {
      DECENTRALIZED_EXCHANGES.map(mod => modules[mod]());
    }
    else if (module === Purgeable.DEFI_MODULES) {
      for (const mod in modules) modules[mod as Module]();
    }
    else {
      const reset = modules[module];

      if (!reset)
        logger.warn(`Missing reset function for ${module}`);
      else reset();
    }
  };

  const reset = (): void => {
    set(allProtocols, {});
    resetState(Purgeable.DEFI_MODULES);
  };

  watch(premium, (premium) => {
    if (!premium)
      reset();
  });

  return {
    allProtocols,
    defiAccounts,
    fetchAllDefi,
    fetchDefiBalances,
    reset,
    resetState,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useDefiStore, import.meta.hot));
