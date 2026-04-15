import type { ActionResult } from '@rotki/common';
import type { TaskMeta } from '@/modules/tasks/types';
import { useAssetsApi } from '@/composables/api/assets';
import { NftResponse } from '@/modules/assets/nfts';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { getDomain } from '@/utils/url';

interface UseNftsReturn {
  fetchNfts: (ignoreCache: boolean) => Promise<ActionResult<NftResponse | null>>;
  shouldRenderImage: (url: string) => boolean;
}

export function useNfts(): UseNftsReturn {
  const { runTask } = useTaskHandler();
  const { t } = useI18n({ useScope: 'global' });

  const assetsApi = useAssetsApi();

  const { renderAllNftImages: renderAll, whitelistedDomainsForNftImages: whitelist }
    = storeToRefs(useFrontendSettingsStore());

  const fetchNfts = async (ignoreCache: boolean): Promise<ActionResult<NftResponse | null>> => {
    const outcome = await runTask<NftResponse, TaskMeta>(
      async () => assetsApi.fetchNfts(ignoreCache),
      { type: TaskType.FETCH_NFTS, meta: { title: t('actions.session.fetch_nfts.task.title') } },
    );

    if (outcome.success) {
      return {
        message: '',
        result: NftResponse.parse(outcome.result),
      };
    }

    return {
      message: isActionableFailure(outcome) ? outcome.message : '',
      result: null,
    };
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
