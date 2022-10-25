import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { useStatusUpdater } from '@/composables/status';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { getStatus, setStatus } from '@/store/status';
import { useTasks } from '@/store/tasks';
import { isLoading } from '@/store/utils';
import {
  ApiMakerDAOVault,
  DSRBalances,
  DSRHistory,
  dsrKeys,
  MakerDAOVault,
  MakerDAOVaultDetails,
  vaultDetailsKeys,
  vaultKeys
} from '@/types/defi/maker';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { bigNumberify, Zero } from '@/utils/bignumbers';

const convertMakerDAOVaults = (vaults: ApiMakerDAOVault[]): MakerDAOVault[] =>
  vaults.map(vault => ({
    ...vault,
    identifier: vault.identifier.toString(),
    protocol: DefiProtocol.MAKERDAO_VAULTS,
    collateral: { ...vault.collateral, asset: vault.collateralAsset },
    collateralizationRatio: vault.collateralizationRatio ?? undefined,
    liquidationPrice: vault.liquidationPrice
      ? vault.liquidationPrice
      : bigNumberify(NaN)
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
  const dsrBalances: Ref<DSRBalances> = ref(
    defaultDsrBalances()
  ) as Ref<DSRBalances>;
  const makerDAOVaults: Ref<MakerDAOVault[]> = ref([]);
  const makerDAOVaultDetails: Ref<MakerDAOVaultDetails[]> = ref([]);

  const { awaitTask } = useTasks();
  const { notify } = useNotifications();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { tc } = useI18n();

  async function fetchDSRBalances(refresh: boolean = false) {
    if (!get(activeModules).includes(Module.MAKERDAO_DSR)) {
      return;
    }
    const section = Section.DEFI_DSR_BALANCES;
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
      const taskType = TaskType.DSR_BALANCE;
      const { taskId } = await api.defi.dsrBalance();
      const { result } = await awaitTask<DSRBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.dsr_balances.task.title'),
          numericKeys: dsrKeys
        }
      );
      set(dsrBalances, result);
    } catch (e: any) {
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

    setStatus(Status.LOADED, section);
  }

  async function fetchDSRHistory(refresh: boolean = false) {
    if (!get(activeModules).includes(Module.MAKERDAO_DSR) || !get(premium)) {
      return;
    }
    const section = Section.DEFI_DSR_HISTORY;
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
      const taskType = TaskType.DSR_HISTORY;
      const { taskId } = await api.defi.dsrHistory();
      const { result } = await awaitTask<DSRHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.dsr_history.task.title'),
          numericKeys: balanceKeys
        }
      );

      set(dsrHistory, result);
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
  }

  async function fetchMakerDAOVaults(refresh: boolean = false) {
    if (!get(activeModules).includes(Module.MAKERDAO_VAULTS)) {
      return;
    }
    const section = Section.DEFI_MAKERDAO_VAULTS;
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
      const taskType = TaskType.MAKEDAO_VAULTS;
      const { taskId } = await api.defi.makerDAOVaults();
      const { result } = await awaitTask<ApiMakerDAOVault[], TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.makerdao_vaults.task.title'),
          numericKeys: vaultKeys
        }
      );

      set(makerDAOVaults, convertMakerDAOVaults(result));
    } catch (e: any) {
      const message = tc(
        'actions.defi.makerdao_vaults.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = tc('actions.defi.makerdao_vaults.error.title');
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  }

  async function fetchMakerDAOVaultDetails(refresh: boolean = false) {
    if (!get(activeModules).includes(Module.MAKERDAO_VAULTS) || !get(premium)) {
      return;
    }
    const section = Section.DEFI_MAKERDAO_VAULT_DETAILS;
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
      const { taskId } = await api.defi.makerDAOVaultDetails();
      const { result } = await awaitTask<MakerDAOVaultDetails[], TaskMeta>(
        taskId,
        TaskType.MAKERDAO_VAULT_DETAILS,
        {
          title: tc('actions.defi.makerdao_vault_details.task.title'),
          numericKeys: vaultDetailsKeys
        }
      );

      set(makerDAOVaultDetails, result);
    } catch (e: any) {
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
  }

  const reset = (protocol?: MakerDAOProtocol) => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_DSR_BALANCES);
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

  return {
    dsrHistory,
    dsrBalances,
    makerDAOVaults,
    makerDAOVaultDetails,
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
