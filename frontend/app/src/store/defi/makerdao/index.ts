import {
  type ApiMakerDAOVault,
  ApiMakerDAOVaults,
  DSRBalances,
  DSRHistory,
  type MakerDAOVault,
  MakerDAOVaultDetails,
} from '@/types/defi/maker';
import { DefiProtocol, Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';
import { getProtocolAddresses } from '@/utils/addresses';
import { isTaskCancelled } from '@/utils';
import { useTaskStore } from '@/store/tasks';
import { useNotificationsStore } from '@/store/notifications';
import { useMakerDaoApi } from '@/composables/api/defi/makerdao';
import { useStatusUpdater } from '@/composables/status';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import type { TaskMeta } from '@/types/task';

function convertMakerDAOVaults(vaults: ApiMakerDAOVault[]): MakerDAOVault[] {
  return vaults.map(vault => ({
    ...vault,
    collateral: { ...vault.collateral, asset: vault.collateralAsset },
    collateralizationRatio: vault.collateralizationRatio ?? undefined,
    identifier: vault.identifier.toString(),
    liquidationPrice: vault.liquidationPrice ? vault.liquidationPrice : bigNumberify(Number.NaN),
    protocol: DefiProtocol.MAKERDAO_VAULTS,
  }));
}

function defaultDsrBalances(): DSRBalances {
  return {
    balances: {},
    currentDsr: Zero,
  };
}

type MakerDAOProtocol = typeof Module.MAKERDAO_DSR | typeof Module.MAKERDAO_VAULTS;

export const useMakerDaoStore = defineStore('defi/makerDao', () => {
  const dsrHistory = ref<DSRHistory>({});
  const dsrBalances = ref<DSRBalances>(defaultDsrBalances());
  const makerDAOVaults = ref<MakerDAOVault[]>([]);
  const makerDAOVaultDetails = ref<MakerDAOVaultDetails>([]);

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { t } = useI18n();
  const {
    fetchDsrBalances: fetchDSRBalancesCaller,
    fetchDsrHistories: fetchDsrHistoriesCaller,
    fetchMakerDAOVaultDetails: fetchMakerDAOVaultDetailsCaller,
    fetchMakerDAOVaults: fetchMakerDAOVaultsCaller,
  } = useMakerDaoApi();

  const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.DEFI_DSR_BALANCES);

  const fetchDSRBalances = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.MAKERDAO_DSR))
      return;

    if (fetchDisabled(refresh))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const taskType = TaskType.DSR_BALANCE;
      const { taskId } = await fetchDSRBalancesCaller();
      const { result } = await awaitTask<DSRBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.dsr_balances.task.title'),
      });
      set(dsrBalances, DSRBalances.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const message = t('actions.defi.dsr_balances.error.description', {
          error: error.message,
        });
        const title = t('actions.defi.dsr_balances.error.title');
        notify({
          display: true,
          message,
          title,
        });
      }
    }

    setStatus(Status.LOADED);
  };

  const fetchDSRHistory = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.MAKERDAO_DSR) || !get(premium))
      return;

    const section = Section.DEFI_DSR_HISTORY;

    if (fetchDisabled(refresh, { section }))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, { section });

    try {
      const taskType = TaskType.DSR_HISTORY;
      const { taskId } = await fetchDsrHistoriesCaller();
      const { result } = await awaitTask<DSRHistory, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.dsr_history.task.title'),
      });

      set(dsrHistory, DSRHistory.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const message = t('actions.defi.dsr_history.error.description', {
          error: error.message,
        });
        const title = t('actions.defi.dsr_history.error.title');
        notify({
          display: true,
          message,
          title,
        });
      }
    }
    setStatus(Status.LOADED, { section });
  };

  const fetchMakerDAOVaults = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.MAKERDAO_VAULTS))
      return;

    const section = Section.DEFI_MAKERDAO_VAULTS;

    if (fetchDisabled(refresh, { section }))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, { section });

    try {
      const taskType = TaskType.MAKERDAO_VAULTS;
      const { taskId } = await fetchMakerDAOVaultsCaller();
      const { result } = await awaitTask<ApiMakerDAOVaults, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.makerdao_vaults.task.title'),
      });

      set(makerDAOVaults, convertMakerDAOVaults(ApiMakerDAOVaults.parse(result)));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const message = t('actions.defi.makerdao_vaults.error.description', {
          error: error.message,
        });
        const title = t('actions.defi.makerdao_vaults.error.title');
        const { notify } = useNotificationsStore();
        notify({
          display: true,
          message,
          title,
        });
      }
    }
    setStatus(Status.LOADED, { section });
  };

  const fetchMakerDAOVaultDetails = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.MAKERDAO_VAULTS) || !get(premium))
      return;

    const section = Section.DEFI_MAKERDAO_VAULT_DETAILS;

    if (fetchDisabled(refresh, { section }))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, { section });

    try {
      const { taskId } = await fetchMakerDAOVaultDetailsCaller();
      const { result } = await awaitTask<MakerDAOVaultDetails, TaskMeta>(taskId, TaskType.MAKERDAO_VAULT_DETAILS, {
        title: t('actions.defi.makerdao_vault_details.task.title'),
      });

      set(makerDAOVaultDetails, MakerDAOVaultDetails.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const message = t('actions.defi.makerdao_vault_details.error.description', { error: error.message });
        const title = t('actions.defi.makerdao_vault_details.error.title');
        notify({
          display: true,
          message,
          title,
        });
      }
    }

    setStatus(Status.LOADED, { section });
  };

  const reset = (protocol?: MakerDAOProtocol): void => {
    if (!protocol || protocol === Module.MAKERDAO_DSR) {
      set(dsrHistory, {});
      set(dsrBalances, defaultDsrBalances());
      resetStatus({ section: Section.DEFI_DSR_BALANCES });
      resetStatus({ section: Section.DEFI_DSR_HISTORY });
    }

    if (!protocol || protocol === Module.MAKERDAO_VAULTS) {
      set(makerDAOVaultDetails, []);
      set(makerDAOVaultDetails, []);
      resetStatus({ section: Section.DEFI_MAKERDAO_VAULTS });
      resetStatus({ section: Section.DEFI_MAKERDAO_VAULT_DETAILS });
    }
  };

  const addresses = computed<string[]>(() =>
    getProtocolAddresses(get(dsrBalances).balances, get(dsrHistory)),
  );

  return {
    addresses,
    dsrBalances,
    dsrHistory,
    fetchDSRBalances,
    fetchDSRHistory,
    fetchMakerDAOVaultDetails,
    fetchMakerDAOVaults,
    makerDAOVaultDetails,
    makerDAOVaults,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMakerDaoStore, import.meta.hot));
