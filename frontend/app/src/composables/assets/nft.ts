import { NftResponse } from '@/types/nfts';
import { TaskType } from '@/types/task-type';
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
        title: t('actions.session.fetch_nfts.task.title').toString(),
      });
      return {
        result: NftResponse.parse(result),
        message: '',
      };
    }
    catch (error: any) {
      return {
        result: null,
        message: error.message,
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
