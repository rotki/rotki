import { wait } from '@shared/utils';
import { useAssetIconApi } from '@/composables/api/assets/icon';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { logger } from '@/modules/common/logging/logging';

export interface AssetCheckOptions {
  abortController?: AbortController;
}

const CACHE_TTL = 5 * 60 * 1000;

interface UseAssetIconCheckReturn {
  checkIfAssetExists: (identifier: string, options: AssetCheckOptions) => Promise<boolean>;
}

export function useAssetIconCheck(): UseAssetIconCheckReturn {
  const { assetExistsCache, pendingIconRequests } = storeToRefs(useAssetsStore());
  const { checkAsset } = useAssetIconApi();

  const checkIfAssetExists = async (identifier: string, options: AssetCheckOptions): Promise<boolean> => {
    const cache = get(assetExistsCache);
    const pending = get(pendingIconRequests);
    const now = Date.now();

    const cached = cache.get(identifier);
    if (cached && (now - cached.timestamp) < CACHE_TTL) {
      return cached.exists;
    }

    const existingRequest = pending.get(identifier);
    if (existingRequest) {
      return existingRequest;
    }

    const request = (async (): Promise<boolean> => {
      let tries = 0;
      try {
        while (tries < 4) {
          const status = await checkAsset(identifier, options);
          if (status === 200 || status === 404) {
            const exists = status === 200;
            cache.set(identifier, { exists, timestamp: Date.now() });
            return exists;
          }

          logger.debug(`Asset ${identifier} check failed with status ${status} (${tries + 1}), waiting`);
          await wait(1500);

          if (options.abortController?.signal.aborted) {
            logger.info('Aborted asset check');
            return false;
          }

          tries++;
        }
        cache.set(identifier, { exists: false, timestamp: Date.now() });
        return false;
      }
      catch (error: unknown) {
        logger.error(error);
        return false;
      }
      finally {
        pending.delete(identifier);
      }
    })();

    pending.set(identifier, request);
    return request;
  };

  return {
    checkIfAssetExists,
  };
}
