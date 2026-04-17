import { wait } from '@shared/utils';
import { useAssetIconApi } from '@/modules/assets/api/use-asset-icon-api';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { logger } from '@/modules/core/common/logging/logging';

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

  const MAX_ATTEMPTS = 4;
  const RETRY_DELAY_MS = 1500;

  async function resolveExists(identifier: string, options: AssetCheckOptions): Promise<boolean> {
    const cache = get(assetExistsCache);
    const pending = get(pendingIconRequests);

    try {
      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        if (options.abortController?.signal.aborted) {
          logger.info('Aborted asset check');
          return false;
        }

        const status = await checkAsset(identifier, options);
        if (status === 200 || status === 404) {
          const exists = status === 200;
          cache.set(identifier, { exists, timestamp: Date.now() });
          return exists;
        }

        if (status !== 202)
          logger.debug(`Asset ${identifier} check failed with status ${status} (${attempt}), waiting`);

        await wait(RETRY_DELAY_MS);
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
  }

  async function checkIfAssetExists(identifier: string, options: AssetCheckOptions): Promise<boolean> {
    const cache = get(assetExistsCache);
    const pending = get(pendingIconRequests);

    const cached = cache.get(identifier);
    if (cached && (Date.now() - cached.timestamp) < CACHE_TTL)
      return cached.exists;

    const existingRequest = pending.get(identifier);
    if (existingRequest)
      return existingRequest;

    const request = resolveExists(identifier, options);
    pending.set(identifier, request);
    return request;
  }

  return {
    checkIfAssetExists,
  };
}
