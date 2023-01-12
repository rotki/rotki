import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Ref } from 'vue';
import { type BtcAccountData } from '@/services/types-api';
import { type XpubPayload } from '@/store/balances/types';
import { useNotificationsStore } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { type BtcChains } from '@/types/blockchain/chains';
import { type BlockchainMetadata } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';
import { removeBtcTags } from '@/utils/tags';

const defaultAccountState = (): BtcAccountData => ({
  standalone: [],
  xpubs: []
});

export const useBtcAccountsStore = defineStore(
  'blockchain/accounts/btc',
  () => {
    const btc: Ref<BtcAccountData> = ref(defaultAccountState());
    const bch: Ref<BtcAccountData> = ref(defaultAccountState());

    const { awaitTask, isTaskRunning } = useTasks();
    const { notify } = useNotificationsStore();
    const { tc } = useI18n();

    const { deleteXpub: deleteXpubCaller } = useBlockchainAccountsApi();

    const deleteXpub = async (payload: XpubPayload) => {
      try {
        const taskType = TaskType.REMOVE_ACCOUNT;
        if (get(isTaskRunning(taskType))) {
          return;
        }
        const { taskId } = await deleteXpubCaller(payload);
        await awaitTask<boolean, BlockchainMetadata>(taskId, taskType, {
          title: tc('actions.balances.xpub_removal.task.title'),
          description: tc('actions.balances.xpub_removal.task.description', 0, {
            xpub: payload.xpub
          }),
          blockchain: payload.blockchain
        });
      } catch (e: any) {
        logger.error(e);
        const title = tc('actions.balances.xpub_removal.error.title');
        const description = tc(
          'actions.balances.xpub_removal.error.description',
          0,
          {
            xpub: payload.xpub,
            error: e.message
          }
        );
        notify({
          title,
          message: description,
          display: true
        });
      }
    };

    const update = (chain: BtcChains, data: BtcAccountData) => {
      if (chain === Blockchain.BTC) {
        set(btc, data);
      } else {
        set(bch, data);
      }
    };

    const removeTag = (tag: string) => {
      set(btc, removeBtcTags(btc, tag));
      set(bch, removeBtcTags(bch, tag));
    };

    return {
      btc,
      bch,
      deleteXpub,
      removeTag,
      update
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useBtcAccountsStore, import.meta.hot));
}
