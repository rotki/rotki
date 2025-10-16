import type { BlockchainAccount } from '@/types/blockchain/accounts';
import type { AssetProtocolBalances } from '@/types/blockchain/balances';
import type { TaskMeta } from '@/types/task';
import { Blockchain } from '@rotki/common';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { AccountAssetBalances } from '@/types/balances';
import { LOOPRING_CHAIN } from '@/types/blockchain';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { balanceSum } from '@/utils/calculation';

interface UseLoopringBalanceServiceReturn {
  fetchLoopringBalances: (refresh: boolean) => Promise<void>;
}

export function useLoopringBalanceService(): UseLoopringBalanceServiceReturn {
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { queryLoopringBalances } = useBlockchainBalancesApi();
  const { updateBalances } = useBalancesStore();
  const { updateAccounts } = useBlockchainAccountsStore();
  const { t } = useI18n({ useScope: 'global' });
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

  const fetchLoopringBalances = async (refresh: boolean): Promise<void> => {
    if (!get(activeModules).includes(Module.LOOPRING))
      return;

    const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.BLOCKCHAIN);

    if (fetchDisabled(refresh, { subsection: LOOPRING_CHAIN }))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, { subsection: LOOPRING_CHAIN });

    try {
      const taskType = TaskType.L2_LOOPRING;
      const { taskId } = await queryLoopringBalances();
      const { result } = await awaitTask<AccountAssetBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.balances.loopring.task.title'),
      });

      const loopringBalances = AccountAssetBalances.parse(result);
      const accounts = Object.keys(loopringBalances).map(address => ({
        chain: LOOPRING_CHAIN,
        data: {
          address,
          type: 'address',
        },
        nativeAsset: Blockchain.ETH.toUpperCase(),
        tags: [],
        virtual: true,
      }) satisfies BlockchainAccount);

      const loopring = Object.fromEntries(
        Object.entries(loopringBalances).map(([address, assets]) => [
          address,
          {
            assets: Object.fromEntries(Object.entries(assets).map(([asset, value]) => [asset, { address: value }])),
            liabilities: {},
          },
        ]),
      );

      const assets: AssetProtocolBalances = {};
      for (const loopringAssets of Object.values(loopringBalances)) {
        for (const [asset, value] of Object.entries(loopringAssets)) {
          const identifier = getAssociatedAssetIdentifier(asset);
          const associatedAsset: string = get(identifier) ?? asset;
          const ownedAsset = assets[associatedAsset];

          if (!ownedAsset)
            assets[associatedAsset] = { address: { ...value } };
          else
            assets[associatedAsset] = { address: { ...balanceSum(ownedAsset.address, value) } };
        }
      }

      const updatedTotals = {
        perAccount: {
          loopring,
        },
        totals: {
          assets,
          liabilities: {},
        },
      };

      updateBalances(LOOPRING_CHAIN, updatedTotals);
      updateAccounts(LOOPRING_CHAIN, accounts);
      setStatus(Status.LOADED, { subsection: LOOPRING_CHAIN });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.balances.loopring.error.description', {
            error: error.message,
          }),
          title: t('actions.balances.loopring.error.title'),
        });
      }
      resetStatus({ subsection: LOOPRING_CHAIN });
    }
  };

  return {
    fetchLoopringBalances,
  };
}
