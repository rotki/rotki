import type { ActionResult } from '@rotki/common';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import { NftResponse } from '@/modules/assets/nfts';
import { getDomain } from '@/modules/core/common/helpers/url';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

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
