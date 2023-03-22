import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { type ComputedRef, type Ref } from 'vue';
import {
  type ApiMakerDAOVault,
  ApiMakerDAOVaults,
  DSRBalances,
  DSRHistory,
  type MakerDAOVault,
  MakerDAOVaultDetails
} from '@/types/defi/maker';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero, bigNumberify } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';
import { getProtocolAddresses } from '@/utils/addresses';

const convertMakerDAOVaults = (vaults: ApiMakerDAOVault[]): MakerDAOVault[] =>
  vaults.map(vault => ({
    ...vault,
    identifier: vault.identifier.toString(),
    protocol: DefiProtocol.MAKERDAO_VAULTS,
    collateral: { ...vault.collateral, asset: vault.collateralAsset },
    collateralizationRatio: vault.collateralizationRatio ?? undefined,
    liquidationPrice: vault.liquidationPrice
      ? vault.liquidationPrice
      : bigNumberify(Number.NaN)
  }));

const defaultDsrBalances = (): DSRBalances => ({
  currentDsr: Zero,
  balances: {}
});

type MakerDAOProtocol =
  | typeof Module.MAKERDAO_DSR
  | typeof Module.MAKERDAO_VAULTS;

export const useMakerDaoStore = defineStore('defi/makerDao', () => {
  const dsrHistory: Ref<DSRHistory> = ref({});
  const dsrBalances: Ref<DSRBalances> = ref(defaultDsrBalances());
  const makerDAOVaults: Ref<MakerDAOVault[]> = ref([]);
  const makerDAOVaultDetails: Ref<MakerDAOVaultDetails> = ref([]);

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { tc } = useI18n();
  const {
    fetchDsrBalances: fetchDSRBalancesCaller,
    fetchDsrHistories: fetchDsrHistoriesCaller,
    fetchMakerDAOVaults: fetchMakerDAOVaultsCaller,
    fetchMakerDAOVaultDetails: fetchMakerDAOVaultDetailsCaller
  } = useMakerDaoApi();

  const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(
    Section.DEFI_DSR_BALANCES
  );

  const fetchDSRBalances = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.MAKERDAO_DSR)) {
      return;
    }
    if (fetchDisabled(refresh)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const taskType = TaskType.DSR_BALANCE;
      const { taskId } = await fetchDSRBalancesCaller();
      const { result } = await awaitTask<DSRBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.dsr_balances.task.title')
        }
      );
      set(dsrBalances, DSRBalances.parse(result));
    } catch (e: any) {
      logger.error(e);
      const message = tc(
        'actions.defi.dsr_balances.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = tc('actions.defi.dsr_balances.error.title');
      notify({
        title,
        message,
        display: true
      });
    }

    setStatus(Status.LOADED);
  };

  const fetchDSRHistory = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.MAKERDAO_DSR) || !get(premium)) {
      return;
    }
    const section = Section.DEFI_DSR_HISTORY;

    if (fetchDisabled(refresh, section)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.DSR_HISTORY;
      const { taskId } = await fetchDsrHistoriesCaller();
      const { result } = await awaitTask<DSRHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.dsr_history.task.title')
        }
      );

      set(dsrHistory, DSRHistory.parse(result));
    } catch (e: any) {
      const message = tc(
        'actions.defi.dsr_history.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = tc('actions.defi.dsr_history.error.title');
      notify({
        title,
        message,
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  };

  const fetchMakerDAOVaults = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.MAKERDAO_VAULTS)) {
      return;
    }
    const section = Section.DEFI_MAKERDAO_VAULTS;

    if (fetchDisabled(refresh, section)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.MAKERDAO_VAULTS;
      const { taskId } = await fetchMakerDAOVaultsCaller();
      const { result } = await awaitTask<ApiMakerDAOVaults, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.makerdao_vaults.task.title')
        }
      );

      set(
        makerDAOVaults,
        convertMakerDAOVaults(ApiMakerDAOVaults.parse(result))
      );
    } catch (e: any) {
      logger.error(e);
      const message = tc(
        'actions.defi.makerdao_vaults.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = tc('actions.defi.makerdao_vaults.error.title');
      const { notify } = useNotificationsStore();
      notify({
        title,
        message,
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  };

  const fetchMakerDAOVaultDetails = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.MAKERDAO_VAULTS) || !get(premium)) {
      return;
    }
    const section = Section.DEFI_MAKERDAO_VAULT_DETAILS;

    if (fetchDisabled(refresh, section)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const { taskId } = await fetchMakerDAOVaultDetailsCaller();
      const { result } = await awaitTask<MakerDAOVaultDetails, TaskMeta>(
        taskId,
        TaskType.MAKERDAO_VAULT_DETAILS,
        {
          title: tc('actions.defi.makerdao_vault_details.task.title')
        }
      );

      set(makerDAOVaultDetails, MakerDAOVaultDetails.parse(result));
    } catch (e: any) {
      logger.error(e);
      const message = tc(
        'actions.defi.makerdao_vault_details.error.description',
        undefined,
        { error: e.message }
      );
      const title = tc('actions.defi.makerdao_vault_details.error.title');
      notify({
        title,
        message,
        display: true
      });
    }

    setStatus(Status.LOADED, section);
  };

  const reset = (protocol?: MakerDAOProtocol): void => {
    if (!protocol || protocol === Module.MAKERDAO_DSR) {
      set(dsrHistory, {});
      set(dsrBalances, defaultDsrBalances());
      resetStatus(Section.DEFI_DSR_BALANCES);
      resetStatus(Section.DEFI_DSR_HISTORY);
    }

    if (!protocol || protocol === Module.MAKERDAO_VAULTS) {
      set(makerDAOVaultDetails, []);
      set(makerDAOVaultDetails, []);
      resetStatus(Section.DEFI_MAKERDAO_VAULTS);
      resetStatus(Section.DEFI_MAKERDAO_VAULT_DETAILS);
    }
  };

  const addresses: ComputedRef<string[]> = computed(() =>
    getProtocolAddresses(get(dsrBalances).balances, get(dsrHistory))
  );

  return {
    dsrHistory,
    dsrBalances,
    makerDAOVaults,
    makerDAOVaultDetails,
    addresses,
    fetchDSRBalances,
    fetchDSRHistory,
    fetchMakerDAOVaults,
    fetchMakerDAOVaultDetails,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useMakerDaoStore, import.meta.hot));
}
