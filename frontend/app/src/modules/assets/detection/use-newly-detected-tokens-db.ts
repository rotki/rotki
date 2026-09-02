import type { Collection as DexieCollection } from 'dexie';
import type { MaybeRef, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { ItemFilter } from '@/modules/user-data/pagination';
import { transformCase } from '@rotki/common';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { logger } from '@/modules/core/common/logging/logging';
import { useSetting } from '@/modules/settings/use-setting';
import { useDatabase } from '@/modules/user-data/use-database';
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

interface ResolvedTokenQuery {
  orderBy: keyof NewDetectedTokenRecord;
  order: 'asc' | 'desc';
  filter?: ItemFilter<NewDetectedTokenRecord>;
}

function resolveTokenQuery(payload: NewDetectedTokensRequestPayload): ResolvedTokenQuery {
  const { ascending = [], orderByAttributes = [], tokenKind } = payload;

  const snakeCaseOrderBy = orderByAttributes.length > 0 ? orderByAttributes[0] : 'detected_at';
  const orderBy = transformCase(snakeCaseOrderBy, true);
  const order = ascending.length > 0 && ascending[0] ? 'asc' : 'desc';
  const filter = tokenKind ? (t: NewDetectedTokenRecord): boolean => t.tokenKind === tokenKind : undefined;

  return { filter, order, orderBy };
}

export const useNewlyDetectedTokensDb = createSharedComposable((): UseNewlyDetectedTokensDbReturn => {
  const isPruning = ref<boolean>(false);

  const { db, isReady } = useDatabase();

  const newlyDetectedTokensMaxCount = useSetting('newlyDetectedTokensMaxCount');
  const newlyDetectedTokensTtlDays = useSetting('newlyDetectedTokensTtlDays');

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
      const payloadValue = get(payload);
      const { limit, offset } = payloadValue;
      const { filter, order, orderBy } = resolveTokenQuery(payloadValue);

      /**
       * Opens a new ordered, filtered collection over the token table.
       *
       * @remarks
       * A fresh one per call, because a Dexie collection is spent once it has been walked: reusing
       * the one that produced the count would yield no rows for the data read.
       */
      const openCollection = (): DexieCollection<NewDetectedTokenRecord, number | undefined> => {
        const ordered = db().newlyDetectedTokens.orderBy(orderBy);
        const directed = order === 'desc' ? ordered.reverse() : ordered;
        return filter ? directed.filter(filter) : directed;
      };

      const total = await db().newlyDetectedTokens.count();
      const found = filter ? await openCollection().count() : total;
      const data = await openCollection().offset(offset).limit(limit).toArray();

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

  /**
   * Expires stale tokens and trims the table back to its configured maximum.
   *
   * @remarks
   * Concurrent calls are dropped rather than queued: several settings watchers and a timer all
   * reach here, and two passes deleting from the same table would race over what the other has
   * already removed. A dropped call is harmless, since the next tick prunes what this one skipped.
   */
  async function prune(): Promise<void> {
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

  watch(isReady, async (ready) => {
    if (ready) {
      await prune();
    }
    else {
      stopPrune();
    }
  });

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
