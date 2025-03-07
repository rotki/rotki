import { useAssetIconApi } from '@/composables/api/assets/icon';
import { isBlockchain } from '@/types/blockchain/chains';
import { logger } from '@/utils/logging';
import { wait } from '@shared/utils';

interface AssetCheckOptions {
  abortController?: AbortController;
}

export const useAssetIconStore = defineStore('assets/icon', () => {
  const lastRefreshedAssetIcon = ref<number>(0);

  const setLastRefreshedAssetIcon = (): void => {
    set(lastRefreshedAssetIcon, Date.now());
  };

  onBeforeMount(() => {
    setLastRefreshedAssetIcon();
  });

  const { assetImageUrl, checkAsset } = useAssetIconApi();

  const getAssetImageUrl = (identifier: string): string => {
    const id = isBlockchain(identifier) ? identifier.toUpperCase() : identifier;
    return assetImageUrl(id, get(lastRefreshedAssetIcon));
  };

  const checkIfAssetExists = async (identifier: string, options: AssetCheckOptions): Promise<boolean> => {
    let tries = 0;
    try {
      while (tries < 4) {
        const status = await checkAsset(identifier, options);
        if (status === 200 || status === 404) {
          return status === 200;
        }

        logger.debug(`Asset ${identifier} check failed with status ${status} (${tries + 1}), waiting`);
        await wait(1500);

        if (options.abortController?.signal.aborted) {
          logger.info('Aborted asset check');
          return false;
        }

        tries++;
      }
      return false;
    }
    catch (error: any) {
      logger.error(error);
      return false;
    }
  };

  return {
    checkIfAssetExists,
    getAssetImageUrl,
    setLastRefreshedAssetIcon,
  };
});
