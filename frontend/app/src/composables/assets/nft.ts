import { NftResponse } from '@/types/nfts';
import { TaskType } from '@/types/task-type';
import { getDomain } from '@/utils/url';
import { useTaskStore } from '@/store/tasks';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useAssetsApi } from '@/composables/api/assets';
import type { ActionResult } from '@rotki/common';
import type { TaskMeta } from '@/types/task';

interface UseNftsReturn {
  fetchNfts: (ignoreCache: boolean) => Promise<ActionResult<NftResponse | null>>;
  shouldRenderImage: (url: string) => boolean;
}

export function useNfts(): UseNftsReturn {
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();

  const assetsApi = useAssetsApi();

  const { renderAllNftImages: renderAll, whitelistedDomainsForNftImages: whitelist }
    = storeToRefs(useFrontendSettingsStore());

  const fetchNfts = async (ignoreCache: boolean): Promise<ActionResult<NftResponse | null>> => {
    try {
      const taskType = TaskType.FETCH_NFTS;
      const { taskId } = await assetsApi.fetchNfts(ignoreCache);
      const { result } = await awaitTask<NftResponse, TaskMeta>(taskId, taskType, {
        title: t('actions.session.fetch_nfts.task.title'),
      });
      return {
        message: '',
        result: NftResponse.parse(result),
      };
    }
    catch (error: any) {
      return {
        message: error.message,
        result: null,
      };
    }
  };

  const shouldRenderImage = (url: string): boolean => {
    if (get(renderAll))
      return true;

    const domain = getDomain(url);
    return get(whitelist).includes(domain);
  };

  return {
    fetchNfts,
    shouldRenderImage,
  };
}
