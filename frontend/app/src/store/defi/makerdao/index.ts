import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { type Ref } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { useNotificationsStore } from '@/store/notifications';
import { getStatus, setStatus } from '@/store/status';
import { useTasks } from '@/store/tasks';
import { isLoading } from '@/store/utils';
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
  const dsrBalances: Ref<DSRBalances> = ref(
    defaultDsrBalances()
  ) as Ref<DSRBalances>;
  const makerDAOVaults: Ref<MakerDAOVault[]> = ref([]);
  const makerDAOVaultDetails: Ref<MakerDAOVaultDetails> = ref([]);

  const { awaitTask } = useTasks();
  const { notify } = useNotificationsStore();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { tc } = useI18n();

  const fetchDSRBalances = async (refresh = false): Promise<void> => {
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

    setStatus(Status.LOADED, section);
  };

  const fetchDSRHistory = async (refresh = false): Promise<void> => {
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
