import type { ActionResult } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import { nftAssetsActivity } from '@/modules/assets/assets.activity';
import { NftResponse } from '@/modules/assets/nfts';
import { getDomain } from '@/modules/core/common/helpers/url';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { activityLabelOf } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseNftsReturn {
  fetchNfts: (ignoreCache: boolean) => Promise<ActionResult<NftResponse | null>>;
  shouldRenderImage: (url: string) => boolean;
}

export function useNfts(): UseNftsReturn {
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  const assetsApi = useAssetsApi();

  const renderAll = useSetting('renderAllNftImages');
  const whitelist = useSetting('whitelistedDomainsForNftImages');

  const fetchNfts = async (ignoreCache: boolean): Promise<ActionResult<NftResponse | null>> => {
    const outcome = await submitTask<NftResponse>({
      id: nftAssetsActivity.id({ ignoreCache }),
      kind: nftAssetsActivity.kind,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<NftResponse, TaskError>> => mapResult(
        await runTask<NftResponse>(
          async () => assetsApi.fetchNfts(ignoreCache),
        ),
        result => NftResponse.parse(result),
      ),
      subtitle: activityLabelOf(nftAssetsActivity),
      title: t('task_center.group.assets'),
    });

    if (!isErr(outcome))
      return { message: '', result: outcome.value };

    return {
      message: isActionable(outcome.error) ? outcome.error.message : '',
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
