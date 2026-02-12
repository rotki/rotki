import { wait } from '@shared/utils';
import { useAssetIconApi } from '@/composables/api/assets/icon';
import { isBlockchain } from '@/types/blockchain/chains';
import { logger } from '@/utils/logging';

interface AssetCheckOptions {
  abortController?: AbortController;
}

interface CachedAssetResult {
  exists: boolean;
  timestamp: number;
}

// Cache TTL: 5 minutes (assets don't change frequently)
const CACHE_TTL = 5 * 60 * 1000;

export const useAssetIconStore = defineStore('assets/icon', () => {
  const lastRefreshedAssetIcon = ref<number>(0);
  // Cache for asset existence checks to avoid redundant HTTP requests
  const assetExistsCache = shallowRef<Map<string, CachedAssetResult>>(new Map());
  // Track pending requests to avoid duplicate in-flight requests
  const pendingRequests = shallowRef<Map<string, Promise<boolean>>>(new Map());

  const setLastRefreshedAssetIcon = (): void => {
    set(lastRefreshedAssetIcon, Date.now());
  };

  const { assetImageUrl, checkAsset } = useAssetIconApi();

  const getAssetImageUrl = (identifier: string): string => {
    const id = isBlockchain(identifier) ? identifier.toUpperCase() : identifier;
    return assetImageUrl(id, get(lastRefreshedAssetIcon));
  };

  const checkIfAssetExists = async (identifier: string, options: AssetCheckOptions): Promise<boolean> => {
    const cache = get(assetExistsCache);
    const pending = get(pendingRequests);
    const now = Date.now();

    // Check cache first
    const cached = cache.get(identifier);
    if (cached && (now - cached.timestamp) < CACHE_TTL) {
      return cached.exists;
    }

    // Check if there's already a pending request for this identifier
    const existingRequest = pending.get(identifier);
    if (existingRequest) {
      return existingRequest;
    }

    // Create new request and track it
    const request = (async (): Promise<boolean> => {
      let tries = 0;
      try {
        while (tries < 4) {
          const status = await checkAsset(identifier, options);
          if (status === 200 || status === 404) {
            const exists = status === 200;
            // Cache the result
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
        // Cache negative result on timeout
        cache.set(identifier, { exists: false, timestamp: Date.now() });
        return false;
      }
      catch (error: any) {
        logger.error(error);
        return false;
      }
      finally {
        // Remove from pending requests
        pending.delete(identifier);
      }
    })();

    pending.set(identifier, request);
    return request;
  };

  // Clear cache when asset icons are refreshed
  watch(lastRefreshedAssetIcon, () => {
    get(assetExistsCache).clear();
    get(pendingRequests).clear();
  });

  return {
    checkIfAssetExists,
    getAssetImageUrl,
    setLastRefreshedAssetIcon,
  };
});
