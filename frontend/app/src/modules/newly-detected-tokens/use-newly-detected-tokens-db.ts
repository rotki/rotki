import type { MaybeRef, Ref } from 'vue';
import type { ItemFilter } from '@/modules/data/pagination';
import type { Collection } from '@/types/collection';
import { transformCase } from '@rotki/common';
import { SECONDS_PER_DAY } from '@/data/constraints';
import { useDatabase } from '@/modules/data/use-database';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { logger } from '@/utils/logging';
import {
  type NewDetectedToken,
  type NewDetectedTokenInput,
  type NewDetectedTokenKind,
  type NewDetectedTokenRecord,
  NewDetectedToken as NewDetectedTokenSchema,
  type NewDetectedTokensRequestPayload,
} from './types';

interface UseNewlyDetectedTokensDbReturn {
  addToken: (token: NewDetectedTokenInput) => Promise<boolean>;
  clearAll: () => Promise<void>;
  count: () => Promise<number>;
  getAllIdentifiers: (tokenKind?: NewDetectedTokenKind) => Promise<string[]>;
  getData: (payload: MaybeRef<NewDetectedTokensRequestPayload>) => Promise<Collection<NewDetectedToken>>;
  isReady: Ref<boolean>;
  isPruning: Ref<boolean>;
  prune: () => Promise<void>;
  removeTokens: (identifiers: string[]) => Promise<void>;
}

const PRUNE_DEBOUNCE_MS = 20000; // 20 seconds debounce for auto-prune

export const useNewlyDetectedTokensDb = createSharedComposable((): UseNewlyDetectedTokensDbReturn => {
  const isPruning = ref<boolean>(false);

  const { db, isReady } = useDatabase();

  const settingsStore = useFrontendSettingsStore();
  const { newlyDetectedTokensMaxCount, newlyDetectedTokensTtlDays } = storeToRefs(settingsStore);

  async function count(): Promise<number> {
    if (!get(isReady))
      return 0;

    try {
      return await db().newlyDetectedTokens.count();
    }
    catch (error) {
      logger.error('Failed to count tokens:', error);
      return 0;
    }
  }

  async function getData(payload: MaybeRef<NewDetectedTokensRequestPayload>): Promise<Collection<NewDetectedToken>> {
    const emptyResult: Collection<NewDetectedToken> = { data: [], found: 0, limit: -1, total: 0 };

    if (!get(isReady))
      return emptyResult;

    try {
      const {
        ascending = [],
        limit,
        offset,
        orderByAttributes = [],
        tokenKind,
      } = get(payload);

      // Convert from snake_case (from usePaginationFilters) to camelCase for IndexedDB
      const snakeCaseOrderBy = orderByAttributes.length > 0 ? orderByAttributes[0] : 'detected_at';
      const orderBy = transformCase(snakeCaseOrderBy, true) as keyof NewDetectedTokenRecord;
      const order = ascending.length > 0 && ascending[0] ? 'asc' : 'desc';

      // Build filter function if needed
      let filter: ItemFilter<NewDetectedTokenRecord> | undefined;
      if (tokenKind) {
        filter = (t): boolean => t.tokenKind === tokenKind;
      }

      // Get total count (unfiltered)
      const total = await db().newlyDetectedTokens.count();

      // Build collection for counting filtered results
      let countCollection = db().newlyDetectedTokens.orderBy(orderBy);
      if (order === 'desc') {
        countCollection = countCollection.reverse();
      }
      const filteredCountCollection = filter ? countCollection.filter(filter) : countCollection;
      const found = filter ? await filteredCountCollection.count() : total;

      // Build fresh collection for data retrieval (don't reuse after count)
      let dataCollection = db().newlyDetectedTokens.orderBy(orderBy);
      if (order === 'desc') {
        dataCollection = dataCollection.reverse();
      }
      const filteredDataCollection = filter ? dataCollection.filter(filter) : dataCollection;
      const data = await filteredDataCollection.offset(offset).limit(limit).toArray();

      return {
        data,
        found,
        limit: -1,
        total,
      };
    }
    catch (error) {
      logger.error('Failed to get tokens:', error);
      return emptyResult;
    }
  }

  async function pruneExpiredTokens(): Promise<void> {
    if (!get(isReady))
      return;

    try {
      const ttlDays = get(newlyDetectedTokensTtlDays);
      const cutoffTime = Date.now() - (ttlDays * SECONDS_PER_DAY * 1000);

      // Get expired token IDs using indexed query, then delete
      const expiredIds = await db().newlyDetectedTokens.where('detectedAt').below(cutoffTime).primaryKeys();

      if (expiredIds.length > 0) {
        await db().newlyDetectedTokens.bulkDelete(expiredIds);
        logger.debug(`Pruned ${expiredIds.length} expired tokens (older than ${ttlDays} days)`);
      }
    }
    catch (error) {
      logger.debug('Failed to prune expired tokens:', error);
    }
  }

  async function pruneExcessTokens(): Promise<void> {
    if (!get(isReady))
      return;

    try {
      const maxCount = get(newlyDetectedTokensMaxCount);
      const totalCount = await db().newlyDetectedTokens.count();

      if (totalCount > maxCount) {
        const toRemove = totalCount - maxCount;

        // Get IDs of oldest tokens using indexed sort and limit
        const idsToRemove = await db().newlyDetectedTokens.orderBy('detectedAt').limit(toRemove).primaryKeys();

        if (idsToRemove.length > 0) {
          await db().newlyDetectedTokens.bulkDelete(idsToRemove);
          logger.debug(`Pruned ${idsToRemove.length} oldest tokens (exceeded max count of ${maxCount})`);
        }
      }
    }
    catch (error) {
      logger.debug('Failed to prune excess tokens:', error);
    }
  }

  async function prune(): Promise<void> {
    // Prevent concurrent prune operations
    if (get(isPruning)) {
      logger.debug('Prune already in progress, skipping');
      return;
    }

    set(isPruning, true);
    try {
      await pruneExpiredTokens();
      await pruneExcessTokens();
    }
    finally {
      set(isPruning, false);
    }
  }

  const { start: startPrune, stop: stopPrune } = useTimeoutFn(async () => {
    await prune();
  }, PRUNE_DEBOUNCE_MS);

  async function addToken(token: NewDetectedTokenInput): Promise<boolean> {
    if (!get(isReady))
      return false;

    try {
      const parsedToken = NewDetectedTokenSchema.parse(token);

      const existingToken = await db().newlyDetectedTokens.where('tokenIdentifier').equals(token.tokenIdentifier).first();

      if (existingToken) {
        await db().newlyDetectedTokens.put({
          ...parsedToken,
          id: existingToken.id,
          detectedAt: existingToken.detectedAt,
        });
        return false;
      }

      await db().newlyDetectedTokens.put(parsedToken);

      stopPrune();
      startPrune();

      return true;
    }
    catch (error) {
      logger.error('Failed to add token:', error);
      return false;
    }
  }

  async function removeTokens(identifiers: string[]): Promise<void> {
    if (!get(isReady) || identifiers.length === 0)
      return;

    try {
      const idsToRemove = await db().newlyDetectedTokens.where('tokenIdentifier').anyOf(identifiers).primaryKeys();

      if (idsToRemove.length > 0) {
        await db().newlyDetectedTokens.bulkDelete(idsToRemove);
      }
    }
    catch (error) {
      logger.error('Failed to remove tokens:', error);
    }
  }

  async function clearAll(): Promise<void> {
    if (!get(isReady))
      return;

    try {
      await db().newlyDetectedTokens.clear();
    }
    catch (error) {
      logger.error('Failed to clear tokens:', error);
    }
  }

  async function getAllIdentifiers(tokenKind?: NewDetectedTokenKind): Promise<string[]> {
    if (!get(isReady))
      return [];

    try {
      let collection = db().newlyDetectedTokens.toCollection();

      if (tokenKind) {
        collection = db().newlyDetectedTokens.where('tokenKind').equals(tokenKind);
      }

      const tokens = await collection.toArray();
      return tokens.map(t => t.tokenIdentifier);
    }
    catch (error) {
      logger.error('Failed to get all identifiers:', error);
      return [];
    }
  }

  // Prune on initialization when database becomes ready
  watch(isReady, async (ready) => {
    if (ready) {
      await prune();
    }
    else {
      stopPrune();
    }
  });

  // Prune when settings change
  watch([newlyDetectedTokensMaxCount, newlyDetectedTokensTtlDays], async ([newMaxCount, newTtl], [oldMaxCount, oldTtl]) => {
    if (newMaxCount === oldMaxCount && newTtl === oldTtl) {
      return;
    }
    if (get(isReady)) {
      await prune();
    }
  });

  return {
    addToken,
    clearAll,
    count,
    getAllIdentifiers,
    getData,
    isReady,
    isPruning,
    prune,
    removeTokens,
  };
});
