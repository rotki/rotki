import { Blockchain } from '@rotki/common/lib/blockchain';
import { TaskType } from '@/types/task-type';
import type { BtcChains } from '@/types/blockchain/chains';
import type { BlockchainMetadata } from '@/types/task';
import type {
  BtcAccountData,
  XpubPayload,
} from '@/types/blockchain/accounts';

function defaultAccountState(): BtcAccountData {
  return {
    standalone: [],
    xpubs: [],
  };
}

export const useBtcAccountsStore = defineStore(
  'blockchain/accounts/btc',
  () => {
    const btc: Ref<BtcAccountData> = ref(defaultAccountState());
    const bch: Ref<BtcAccountData> = ref(defaultAccountState());

    const { awaitTask, isTaskRunning } = useTaskStore();
    const { notify } = useNotificationsStore();
    const { t } = useI18n();

    const { deleteXpub: deleteXpubCaller } = useBlockchainAccountsApi();

    const deleteXpub = async (payload: XpubPayload) => {
      try {
        const taskType = TaskType.REMOVE_ACCOUNT;
        if (get(isTaskRunning(taskType)))
          return;

        const { taskId } = await deleteXpubCaller(payload);
        await awaitTask<boolean, BlockchainMetadata>(taskId, taskType, {
          title: t('actions.balances.xpub_removal.task.title'),
          description: t('actions.balances.xpub_removal.task.description', {
            xpub: payload.xpub,
          }),
          blockchain: payload.blockchain,
        });
      }
      catch (error: any) {
        if (!isTaskCancelled(error)) {
          logger.error(error);
          const title = t('actions.balances.xpub_removal.error.title');
          const description = t(
            'actions.balances.xpub_removal.error.description',
            {
              xpub: payload.xpub,
              error: error.message,
            },
          );
          notify({
            title,
            message: description,
            display: true,
          });
        }
      }
    };

    const update = (chain: BtcChains, data: BtcAccountData) => {
      if (chain === Blockchain.BTC)
        set(btc, data);
      else
        set(bch, data);
    };

    const removeTag = (tag: string) => {
      set(btc, removeBtcTags(btc, tag));
      set(bch, removeBtcTags(bch, tag));
    };

    const getAddresses = (items: BtcAccountData) =>
      [
        ...items.standalone.map(({ address }) => address),
        ...items.xpubs.flatMap(({ addresses }) => addresses ?? []).map(({ address }) => address),
      ].filter(uniqueStrings);

    const btcAddresses: ComputedRef<string[]> = computed(() => getAddresses(get(btc)));

    const bchAddresses: ComputedRef<string[]> = computed(() => getAddresses(get(bch)));

    return {
      btc,
      bch,
      btcAddresses,
      bchAddresses,
      deleteXpub,
      removeTag,
      update,
    };
  },
);

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBtcAccountsStore, import.meta.hot));
