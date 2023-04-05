import { type ActionResult } from '@rotki/common/lib/data';
import { getDomain } from '@/utils/url';
import { NftResponse } from '@/types/nfts';
import { TaskType } from '@/types/task-type';
import { type TaskMeta } from '@/types/task';

export const useNfts = () => {
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();

  const assetsApi = useAssetsApi();

  const {
    renderAllNftImages: renderAll,
    whitelistedDomainsForNftImages: whitelist
  } = storeToRefs(useFrontendSettingsStore());

  const fetchNfts = async (
    ignoreCache: boolean
  ): Promise<ActionResult<NftResponse | null>> => {
    try {
      const taskType = TaskType.FETCH_NFTS;
      const { taskId } = await assetsApi.fetchNfts(ignoreCache);
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

  const shouldRenderImage = (url: string) => {
    if (get(renderAll)) {
      return true;
    }

    const domain = getDomain(url);
    return get(whitelist).includes(domain);
  };

  return {
    fetchNfts,
    shouldRenderImage
  };
};
