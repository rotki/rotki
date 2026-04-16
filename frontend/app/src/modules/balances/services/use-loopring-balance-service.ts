import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { AssetProtocolBalances } from '@/modules/balances/types/blockchain-balances';
import type { TaskMeta } from '@/modules/tasks/types';
import { Blockchain } from '@rotki/common';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useResolveAssetIdentifier } from '@/composables/assets/common';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { AccountAssetBalances } from '@/modules/balances/types/balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { balanceSum } from '@/modules/common/data/calculation';
import { Module } from '@/modules/common/modules';
import { Section, Status } from '@/modules/common/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { LOOPRING_CHAIN } from '@/modules/onchain/blockchain-types';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';

interface UseLoopringBalanceServiceReturn {
  fetchLoopringBalances: (refresh: boolean) => Promise<void>;
}

export function useLoopringBalanceService(): UseLoopringBalanceServiceReturn {
  const { runTask } = useTaskHandler();
  const { notifyError } = useNotifications();
  const { queryLoopringBalances } = useBlockchainBalancesApi();
  const { updateBalances } = useBalancesStore();
  const { updateAccounts } = useBlockchainAccountsStore();
  const { t } = useI18n({ useScope: 'global' });
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const resolveAssetIdentifier = useResolveAssetIdentifier();

  const fetchLoopringBalances = async (refresh: boolean): Promise<void> => {
    if (!get(activeModules).includes(Module.LOOPRING))
      return;

    const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.BLOCKCHAIN);

    if (fetchDisabled(refresh, { subsection: LOOPRING_CHAIN }))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, { subsection: LOOPRING_CHAIN });

    const outcome = await runTask<AccountAssetBalances, TaskMeta>(
      async () => queryLoopringBalances(),
      { type: TaskType.L2_LOOPRING, meta: { title: t('actions.balances.loopring.task.title') } },
    );

    if (outcome.success) {
      const loopringBalances = AccountAssetBalances.parse(outcome.result);
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
          const associatedAsset: string = resolveAssetIdentifier(asset);
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
    else {
      if (isActionableFailure(outcome)) {
        notifyError(
          t('actions.balances.loopring.error.title'),
          t('actions.balances.loopring.error.description', {
            error: outcome.message,
          }),
        );
      }
      resetStatus({ subsection: LOOPRING_CHAIN });
    }
  };

  return {
    fetchLoopringBalances,
  };
}
