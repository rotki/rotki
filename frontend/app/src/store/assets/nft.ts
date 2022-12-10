import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import { NftResponse } from '@/store/session/types';
import { useTasks } from '@/store/tasks';
import { type AssetInfoWithId } from '@/types/assets';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

/**
 * It is like {@link AssetInfoWithId} but with two extra properties for
 * NFTs. It contains an imageUrl (optional) which is the image associated
 * with the NFT and a collectionName (optional)
 */
export interface NftAsset extends AssetInfoWithId {
  imageUrl?: string;
  collectionName?: string;
}

export const useNftsStore = defineStore('assets/nfts', () => {
  const { awaitTask } = useTasks();
  const { t } = useI18n();

  const fetchNfts = async (
    ignoreCache: boolean
  ): Promise<ActionResult<NftResponse | null>> => {
    try {
      const taskType = TaskType.FETCH_NFTS;
      const { taskId } = await api.fetchNfts(ignoreCache);
      const { result } = await awaitTask<NftResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.session.fetch_nfts.task.title').toString()
        }
      );
      return {
        result: NftResponse.parse(result),
        message: ''
      };
    } catch (e: any) {
      return {
        result: null,
        message: e.message
      };
    }
  };

  return {
    fetchNfts
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useNftsStore, import.meta.hot));
}
