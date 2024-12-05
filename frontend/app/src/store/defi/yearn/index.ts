import { type YearnVaultAsset, type YearnVaultBalance, YearnVaultsBalances } from '@/types/defi/yearn';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { ProtocolVersion } from '@/types/defi';
import { isTaskCancelled } from '@/utils';
import { getProtocolAddresses } from '@/utils/addresses';
import { balanceSum } from '@/utils/calculation';
import { zeroBalance } from '@/utils/bignumbers';
import { useTaskStore } from '@/store/tasks';
import { useNotificationsStore } from '@/store/notifications';
import { useYearnApi } from '@/composables/api/defi/yearn';
import { useStatusUpdater } from '@/composables/status';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useModules } from '@/composables/session/modules';
import type { TaskMeta } from '@/types/task';

export const useYearnStore = defineStore('defi/yearn', () => {
  const vaultsBalances = ref<YearnVaultsBalances>({});
  const vaultsV2Balances = ref<YearnVaultsBalances>({});

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { activeModules } = useModules();
  const { assetSymbol } = useAssetInfoRetrieval();
  const { t } = useI18n();
  const { fetchYearnVaultsBalances } = useYearnApi();

  const { fetchDisabled, setStatus } = useStatusUpdater(Section.DEFI_YEARN_VAULTS_BALANCES);

  const yearnVaultsAssets = (
    addresses: string[],
    version: ProtocolVersion = ProtocolVersion.V1,
  ): ComputedRef<YearnVaultAsset[]> => computed<YearnVaultAsset[]>(() => {
    const vaultBalances = get(version === ProtocolVersion.V1 ? vaultsBalances : vaultsV2Balances);
    const balances: Record<string, YearnVaultBalance[]> = {};
    const allAddresses = addresses.length === 0;
    for (const address in vaultBalances) {
      if (!allAddresses && !addresses.includes(address))
        continue;

      const vaults = vaultBalances[address];
      for (const vault in vaults) {
        let vaultName = vault;

        if (vault.startsWith('0x')) {
          const tokenSymbol = get(assetSymbol(vaults[vault].vaultToken));
          vaultName = `${tokenSymbol} Vault`;
        }

        const balance = vaults[vault];
        if (!balance)
          continue;

        if (!balances[vaultName])
          balances[vaultName] = [balance];
        else balances[vaultName].push(balance);
      }
    }

    const vaultAssets: YearnVaultAsset[] = [];
    for (const key in balances) {
      const allBalances = balances[key];
      const { roi, underlyingToken, vaultToken } = allBalances[0];

      const underlyingValue = zeroBalance();
      const vaultValue = zeroBalance();
      const values = { underlyingValue, vaultValue };
      const summary = allBalances.reduce(
        (sum, current) => ({
          underlyingValue: balanceSum(sum.underlyingValue, current.underlyingValue),
          vaultValue: balanceSum(sum.vaultValue, current.vaultValue),
        }),
        values,
      );
      vaultAssets.push({
        roi,
        underlyingToken,
        underlyingValue: summary.underlyingValue,
        vault: key,
        vaultToken,
        vaultValue: summary.vaultValue,
        version,
      });
    }
    return vaultAssets;
  });

  async function fetchBalances(
    { refresh, version }: { refresh: boolean; version: ProtocolVersion } = {
      refresh: false,
      version: ProtocolVersion.V1,
    },
  ): Promise<void> {
    const isV1 = version === ProtocolVersion.V1;
    const isV2 = version === ProtocolVersion.V2;
    const modules = get(activeModules);
    const isYearnV1AndActive = modules.includes(Module.YEARN) && isV1;
    const isYearnV2AndActive = modules.includes(Module.YEARN_V2) && isV2;
    const isModuleActive = isYearnV1AndActive || isYearnV2AndActive;

    if (!isModuleActive)
      return;

    const section = isV1 ? Section.DEFI_YEARN_VAULTS_BALANCES : Section.DEFI_YEARN_VAULTS_V2_BALANCES;

    if (fetchDisabled(refresh, { section }))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, { section });
    try {
      const taskType = isV1 ? TaskType.DEFI_YEARN_VAULT_BALANCES : TaskType.DEFI_YEARN_VAULT_V2_BALANCES;
      const { taskId } = await fetchYearnVaultsBalances(version);
      const { result } = await awaitTask<YearnVaultsBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.yearn_vaults.task.title', {
          version,
        }),
      });

      const balances = YearnVaultsBalances.parse(result);
      if (isV1)
        set(vaultsBalances, balances);
      else set(vaultsV2Balances, balances);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.defi.yearn_vaults.error.description', {
            error: error.message,
            version,
          }),
          title: t('actions.defi.yearn_vaults.error.title', {
            version,
          }),
        });
      }
    }
    setStatus(Status.LOADED, { section });
  }

  const reset = (version?: ProtocolVersion): void => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_YEARN_VAULTS_BALANCES);
    if (!version || version === ProtocolVersion.V1) {
      set(vaultsBalances, {});
      resetStatus({ section: Section.DEFI_YEARN_VAULTS_BALANCES });
      resetStatus({ section: Section.DEFI_YEARN_VAULTS_HISTORY });
    }

    if (!version || version === ProtocolVersion.V2) {
      set(vaultsV2Balances, {});
      resetStatus({ section: Section.DEFI_YEARN_VAULTS_V2_BALANCES });
      resetStatus({ section: Section.DEFI_YEARN_VAULTS_V2_HISTORY });
    }
  };

  const addressesV1 = computed<string[]>(() => getProtocolAddresses(get(vaultsBalances), []));

  const addressesV2 = computed<string[]>(() => getProtocolAddresses(get(vaultsV2Balances), []));

  return {
    addressesV1,
    addressesV2,
    fetchBalances,
    reset,
    vaultsBalances,
    vaultsV2Balances,
    yearnVaultsAssets,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useYearnStore, import.meta.hot));
