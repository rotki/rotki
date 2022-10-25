import { ComputedRef, Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { useStatusUpdater } from '@/composables/status';
import { balanceKeys } from '@/services/consts';
import { ProtocolVersion } from '@/services/defi/consts';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useNotifications } from '@/store/notifications';
import { getStatus, setStatus } from '@/store/status';
import { useTasks } from '@/store/tasks';
import { isLoading } from '@/store/utils';
import {
  DEPOSIT,
  YearnVaultAsset,
  YearnVaultBalance,
  YearnVaultProfitLoss,
  YearnVaultsBalances,
  YearnVaultsHistory
} from '@/types/defi/yearn';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { isEvmIdentifier } from '@/utils/assets';
import { zeroBalance } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';

export const useYearnStore = defineStore('defi/yearn', () => {
  const vaultsBalances: Ref<YearnVaultsBalances> = ref({});
  const vaultsHistory: Ref<YearnVaultsHistory> = ref({});
  const vaultsV2Balances: Ref<YearnVaultsBalances> = ref({});
  const vaultsV2History: Ref<YearnVaultsHistory> = ref({});

  const { awaitTask } = useTasks();
  const { notify } = useNotifications();
  const { activeModules } = useModules();
  const { assetSymbol } = useAssetInfoRetrieval();
  const premium = usePremium();
  const { t } = useI18n();

  const yearnVaultsProfit = (
    addresses: string[],
    version: ProtocolVersion = ProtocolVersion.V1
  ): ComputedRef<YearnVaultProfitLoss[]> =>
    computed(() => {
      const vaultHistory = get(
        version === ProtocolVersion.V1 ? vaultsHistory : vaultsV2History
      );
      const yearnVaultsProfit: { [vault: string]: YearnVaultProfitLoss } = {};
      const allAddresses = addresses.length === 0;
      for (const address in vaultHistory) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }
        const history = vaultHistory[address];
        for (const vault in history) {
          const data = history[vault];
          if (!data) {
            continue;
          }

          const events = data.events.filter(
            event => event.eventType === DEPOSIT
          );
          const asset = events && events.length > 0 ? events[0].fromAsset : '';

          if (!yearnVaultsProfit[vault]) {
            let vaultName = vault;
            if (isEvmIdentifier(vault)) {
              vaultName = `${get(assetSymbol(vault))} Vault`;
            }

            yearnVaultsProfit[vault] = {
              value: data.profitLoss,
              vault: vaultName,
              asset
            };
          } else {
            yearnVaultsProfit[vault] = {
              ...yearnVaultsProfit[vault],
              value: balanceSum(yearnVaultsProfit[vault].value, data.profitLoss)
            };
          }
        }
      }
      return Object.values(yearnVaultsProfit);
    });

  const yearnVaultsAssets = (
    addresses: string[],
    version: ProtocolVersion = ProtocolVersion.V1
  ) =>
    computed(() => {
      const vaultBalances = get(
        version === ProtocolVersion.V1 ? vaultsBalances : vaultsV2Balances
      );
      const balances: { [vault: string]: YearnVaultBalance[] } = {};
      const allAddresses = addresses.length === 0;
      for (const address in vaultBalances) {
        if (!allAddresses && !addresses.includes(address)) {
          continue;
        }

        const vaults = vaultBalances[address];
        for (const vault in vaults) {
          let vaultName = vault;

          if (vault.startsWith('0x')) {
            const tokenSymbol = get(assetSymbol(vaults[vault].vaultToken));
            vaultName = `${tokenSymbol} Vault`;
          }

          const balance = vaults[vault];
          if (!balance) {
            continue;
          }

          if (!balances[vaultName]) {
            balances[vaultName] = [balance];
          } else {
            balances[vaultName].push(balance);
          }
        }
      }

      const vaultAssets: YearnVaultAsset[] = [];
      for (const key in balances) {
        const allBalances = balances[key];
        const { underlyingToken, vaultToken, roi } = allBalances[0];

        const underlyingValue = zeroBalance();
        const vaultValue = zeroBalance();
        const values = { underlyingValue, vaultValue };
        const summary = allBalances.reduce((sum, current) => {
          return {
            vaultValue: balanceSum(sum.vaultValue, current.vaultValue),
            underlyingValue: balanceSum(
              sum.underlyingValue,
              current.underlyingValue
            )
          };
        }, values);
        vaultAssets.push({
          vault: key,
          version,
          underlyingToken,
          underlyingValue: summary.underlyingValue,
          vaultToken,
          vaultValue: summary.vaultValue,
          roi
        });
      }

      return vaultAssets;
    });

  async function fetchBalances(
    { refresh, version }: { refresh: boolean; version: ProtocolVersion } = {
      refresh: false,
      version: ProtocolVersion.V1
    }
  ) {
    const isV1 = version === ProtocolVersion.V1;
    const isV2 = version === ProtocolVersion.V2;
    const modules = get(activeModules);
    const isYearnV1AndActive = modules.includes(Module.YEARN) && isV1;
    const isYearnV2AndActive = modules.includes(Module.YEARN_V2) && isV2;
    const isModuleActive = isYearnV1AndActive || isYearnV2AndActive;

    if (!isModuleActive) {
      return;
    }

    const section = isV1
      ? Section.DEFI_YEARN_VAULTS_BALANCES
      : Section.DEFI_YEARN_VAULTS_V2_BALANCES;
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
      const taskType = isV1
        ? TaskType.DEFI_YEARN_VAULT_BALANCES
        : TaskType.DEFI_YEARN_VAULT_V2_BALANCES;
      const { taskId } = await api.defi.fetchYearnVaultsBalances(version);
      const { result } = await awaitTask<YearnVaultsBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.defi.yearn_vaults.task.title', {
            version
          }).toString(),
          numericKeys: balanceKeys
        }
      );

      if (isV1) {
        set(vaultsBalances, result);
      } else {
        set(vaultsV2Balances, result);
      }
    } catch (e: any) {
      notify({
        title: t('actions.defi.yearn_vaults.error.title', {
          version
        }).toString(),
        message: t('actions.defi.yearn_vaults.error.description', {
          error: e.message,
          version
        }).toString(),
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  }

  async function fetchHistory(payload: {
    refresh?: boolean;
    reset?: boolean;
    version: ProtocolVersion;
  }) {
    const refresh = payload?.refresh;
    const reset = payload?.reset;

    const isV1 = payload.version === ProtocolVersion.V1;
    const isV2 = payload.version === ProtocolVersion.V2;

    const modules = get(activeModules);
    const isYearnV1AndActive = modules.includes(Module.YEARN) && isV1;
    const isYearnV2AndActive = modules.includes(Module.YEARN_V2) && isV2;
    const isModuleActive = isYearnV1AndActive || isYearnV2AndActive;

    if (!isModuleActive || !get(premium)) {
      return;
    }

    const section = isV1
      ? Section.DEFI_YEARN_VAULTS_HISTORY
      : Section.DEFI_YEARN_VAULTS_V2_HISTORY;
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
      const taskType = isV1
        ? TaskType.DEFI_YEARN_VAULT_HISTORY
        : TaskType.DEFI_YEARN_VAULT_V2_HISTORY;
      const { taskId } = await api.defi.fetchYearnVaultsHistory(
        payload.version,
        reset
      );
      const { result } = await awaitTask<YearnVaultsHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.defi.yearn_vaults_history.task.title', {
            version: payload.version
          }).toString(),
          numericKeys: balanceKeys
        }
      );

      if (isV1) {
        set(vaultsHistory, result);
      } else {
        set(vaultsV2History, result);
      }
    } catch (e: any) {
      notify({
        title: t('actions.defi.yearn_vaults_history.error.title', {
          version: payload.version
        }).toString(),
        message: t('actions.defi.yearn_vaults_history.error.description', {
          error: e.message,
          version: payload.version
        }).toString(),
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  }

  const reset = (version?: ProtocolVersion) => {
    const { resetStatus } = useStatusUpdater(
      Section.DEFI_YEARN_VAULTS_BALANCES
    );
    if (!version || version === ProtocolVersion.V1) {
      set(vaultsBalances, {});
      set(vaultsHistory, {});
      resetStatus(Section.DEFI_YEARN_VAULTS_BALANCES);
      resetStatus(Section.DEFI_YEARN_VAULTS_HISTORY);
    }

    if (!version || version === ProtocolVersion.V2) {
      set(vaultsV2Balances, {});
      set(vaultsV2History, {});
      resetStatus(Section.DEFI_YEARN_VAULTS_V2_BALANCES);
      resetStatus(Section.DEFI_YEARN_VAULTS_V2_HISTORY);
    }
  };

  return {
    vaultsBalances,
    vaultsHistory,
    vaultsV2Balances,
    vaultsV2History,
    yearnVaultsProfit,
    yearnVaultsAssets,
    fetchBalances,
    fetchHistory,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useYearnStore, import.meta.hot));
}
