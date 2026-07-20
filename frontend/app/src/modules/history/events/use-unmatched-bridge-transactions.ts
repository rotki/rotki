import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { TaskMeta } from '@/modules/core/tasks/types';
import type { LinkedMovementMatch } from '@/modules/history/events/event-payloads';
import type { MatchingFlow, UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { HistoryEventCollectionRow, HistoryEventEntryWithMeta } from '@/modules/history/events/schemas';
import { NotificationGroup } from '@rotki/common';
import { z } from 'zod';
import { arrayify } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useBridgeMatchingApi } from '@/modules/history/api/events/use-bridge-matching-api';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useBridgeMatchSettings } from '@/modules/settings/use-bridge-match-settings';

/** The bridge leg metadata the decoders record in the event's extra data. */
const BridgeExtraData = z.object({
  fromChain: z.union([z.string(), z.number()]).optional(),
  toChain: z.union([z.string(), z.number()]).optional(),
  fromAddress: z.string().optional(),
  toAddress: z.string().optional(),
  transferId: z.string().optional(),
});

export type BridgeExtraData = z.infer<typeof BridgeExtraData>;

const BridgeEventExtraData = z.object({
  bridge: BridgeExtraData.optional(),
  matchedBridge: z.object({
    direction: z.enum(['deposit', 'withdrawal']).optional(),
  }).optional(),
});

/** Extracts the recorded bridge metadata from an event's raw extra data, if any. */
export function getBridgeExtraData(extraData: unknown): BridgeExtraData | undefined {
  const parsed = BridgeEventExtraData.safeParse(extraData);
  return parsed.success ? parsed.data.bridge : undefined;
}

/**
 * Extracts the original direction of a bridge leg that was resolved as external.
 * The resolution turns the event into a plain spend/receive, so the direction
 * can no longer be derived from the event type itself.
 */
export function getResolvedBridgeDirection(extraData: unknown): 'deposit' | 'withdrawal' | undefined {
  const parsed = BridgeEventExtraData.safeParse(extraData);
  return parsed.success ? parsed.data.matchedBridge?.direction : undefined;
}

/** The bridge leg direction, from the external-resolution stamp or the event type. */
function deriveBridgeDirection(extraData: unknown, eventType?: string): 'deposit' | 'withdrawal' {
  return getResolvedBridgeDirection(extraData) ?? (eventType === 'withdrawal' ? 'withdrawal' : 'deposit');
}

export interface UnmatchedBridgeTransaction extends UnmatchedEventGroup {
  direction: 'deposit' | 'withdrawal';
  bridge?: BridgeExtraData;
}

/**
 * Picks the bridge leg out of a group. A bridge group is keyed by the EVM transaction
 * hash, so it also contains the gas fee event (and possibly others). Only the bridge leg
 * is the one the matching endpoints accept, so it has to be selected explicitly instead
 * of taking the first event of the group. A raw leg is a deposit/withdrawal with the
 * `bridge` subtype; a leg resolved as external is turned into a plain spend/receive but
 * keeps the `matchedBridge` stamp, which is what tells it apart from the gas fee event.
 */
function findBridgeEntry(events: HistoryEventEntryWithMeta[]): HistoryEventEntryWithMeta | undefined {
  return events.find(({ entry }) => {
    if (entry.eventSubtype === 'bridge' && (entry.eventType === 'deposit' || entry.eventType === 'withdrawal'))
      return true;
    return getResolvedBridgeDirection('extraData' in entry ? entry.extraData : undefined) !== undefined;
  });
}

interface UseUnmatchedBridgeTransactionsReturn {
  unmatchedTransactions: ComputedRef<UnmatchedBridgeTransaction[]>;
  ignoredTransactions: ComputedRef<UnmatchedBridgeTransaction[]>;
  unmatchedCount: ComputedRef<number>;
  ignoredCount: ComputedRef<number>;
  loading: Ref<boolean>;
  ignoredLoading: Ref<boolean>;
  autoMatchLoading: ComputedRef<boolean>;
  autoMatchMinimumTier: Readonly<Ref<string | null>>;
  isAutoMatchAllowed: Readonly<Ref<boolean>>;
  autoMatchBridgeTransaction: (linkedTransaction: LinkedMovementMatch) => Promise<boolean>;
  fetchUnmatchedBridgeTransactions: (onlyIgnored?: boolean) => Promise<void>;
  matchBridgeTransaction: (bridgeEventId: number, matchedEventIds: number[]) => Promise<ActionStatus>;
  resolveExternal: (bridgeEventId: number) => Promise<ActionStatus>;
  refreshUnmatchedBridgeTransactions: (skipIgnored?: boolean) => Promise<void>;
  triggerBridgeAutoMatching: () => Promise<void>;
}

const rawUnmatchedTransactions = ref<UnmatchedBridgeTransaction[]>([]);
const rawIgnoredTransactions = ref<UnmatchedBridgeTransaction[]>([]);
const loading = ref<boolean>(false);
const ignoredLoading = ref<boolean>(false);
const triggerAutoMatchLoading = ref<boolean>(false);

export const useUnmatchedBridgeTransactions = createSharedComposable((): UseUnmatchedBridgeTransactionsReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { removeMatching, showErrorMessage, showSuccessMessage } = useNotifications();
  const { runTask } = useTaskHandler();
  const { useIsTaskRunning } = useTaskStore();

  const { fetchHistoryEvents } = useHistoryEventsApi();
  const {
    getBridgeMatches,
    getUnmatchedBridgeTransactions,
    matchBridgeTransactions: matchBridgeTransactionsApi,
    triggerBridgeMatching,
  } = useBridgeMatchingApi();
  const { signalEventsModified } = useHistoryStore();
  const { allowed: isBridgeMatchingAllowed, minimumTier: bridgeMatchingMinimumTier } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

  const isTaskRunning = useIsTaskRunning(TaskType.MATCH_BRIDGE_TRANSACTIONS);
  const autoMatchLoading = logicOr(triggerAutoMatchLoading, isTaskRunning);

  const unmatchedTransactions = computed<UnmatchedBridgeTransaction[]>(() => get(rawUnmatchedTransactions));
  const ignoredTransactions = computed<UnmatchedBridgeTransaction[]>(() => get(rawIgnoredTransactions));

  const unmatchedCount = computed<number>(() => get(unmatchedTransactions).length);
  const ignoredCount = computed<number>(() => get(ignoredTransactions).length);

  function clearUnmatchedBridgeTransactionsNotification(): void {
    removeMatching(notification => notification.group === NotificationGroup.UNMATCHED_BRIDGE_TRANSACTIONS);
  }

  const fetchUnmatchedBridgeTransactions = async (onlyIgnored?: boolean): Promise<void> => {
    const isIgnored = onlyIgnored === true;
    const loadingRef = isIgnored ? ignoredLoading : loading;
    const transactionsRef = isIgnored ? rawIgnoredTransactions : rawUnmatchedTransactions;

    set(loadingRef, true);
    try {
      const groupIdentifiers = await getUnmatchedBridgeTransactions(onlyIgnored);

      if (groupIdentifiers.length === 0) {
        set(transactionsRef, []);
        if (!isIgnored)
          clearUnmatchedBridgeTransactionsNotification();
        return;
      }

      const response = await fetchHistoryEvents({
        aggregateByGroupIds: false,
        groupIdentifiers,
        limit: -1,
        offset: 0,
        orderByAttributes: ['timestamp'],
        ascending: [false],
      });

      const transactions: UnmatchedBridgeTransaction[] = [];

      for (const groupId of groupIdentifiers) {
        const eventsForGroup = response.entries.filter((row) => {
          const events = arrayify(row);
          return events.some(event => event.entry.groupIdentifier === groupId);
        });

        if (eventsForGroup.length > 0) {
          // The events of a group come back as separate rows, so the bridge leg has to be looked
          // for across all of them: the first row is the gas fee event, not the bridge event.
          const bridgeMatch = eventsForGroup
            .map(row => ({ event: findBridgeEntry(arrayify(row)), row }))
            .find((candidate): candidate is { event: HistoryEventEntryWithMeta; row: HistoryEventCollectionRow } => !!candidate.event);

          if (!bridgeMatch) {
            logger.warn(`No bridge event found in group ${groupId}, skipping it`);
            continue;
          }

          const entry = bridgeMatch.event.entry;
          const extraData = 'extraData' in entry ? entry.extraData : undefined;

          transactions.push({
            asset: entry.asset,
            bridge: getBridgeExtraData(extraData),
            direction: deriveBridgeDirection(extraData, entry.eventType),
            events: bridgeMatch.row,
            groupIdentifier: groupId,
            identifier: entry.identifier,
          });
        }
      }

      set(transactionsRef, transactions);
    }
    catch (error: unknown) {
      logger.error('Failed to fetch unmatched bridge transactions:', error);
      showErrorMessage(t('actions.bridge_matching.fetch_error.title'), t('actions.bridge_matching.fetch_error.description', { error: getErrorMessage(error) }));
    }
    finally {
      set(loadingRef, false);
    }
  };

  const matchBridgeTransaction = async (
    bridgeEventId: number,
    matchedEventIds: number[],
  ): Promise<ActionStatus> => {
    try {
      const success = await matchBridgeTransactionsApi(bridgeEventId, matchedEventIds);

      if (success) {
        showSuccessMessage(t('actions.bridge_matching.success.title'), t('actions.bridge_matching.success.description'));
        signalEventsModified();
      }

      return { message: '', success };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      logger.error('Failed to match bridge transaction:', error);
      showErrorMessage(t('actions.bridge_matching.error.title'), t('actions.bridge_matching.error.description', { error: message }));
      return { message, success: false };
    }
  };

  const resolveExternal = async (bridgeEventId: number): Promise<ActionStatus> => {
    try {
      const success = await matchBridgeTransactionsApi(bridgeEventId, undefined, true);

      if (success) {
        showSuccessMessage(t('actions.bridge_matching.external_success.title'), t('actions.bridge_matching.external_success.description'));
        signalEventsModified();
      }

      return { message: '', success };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      logger.error('Failed to resolve bridge transaction as external:', error);
      showErrorMessage(t('actions.bridge_matching.error.title'), t('actions.bridge_matching.error.description', { error: message }));
      return { message, success: false };
    }
  };

  const refreshUnmatchedBridgeTransactions = async (skipIgnored = false): Promise<void> => {
    await fetchUnmatchedBridgeTransactions();
    if (!skipIgnored) {
      await fetchUnmatchedBridgeTransactions(true);
    }
  };

  const triggerBridgeAutoMatching = async (): Promise<void> => {
    if (!get(isBridgeMatchingAllowed) || get(isTaskRunning))
      return;

    set(triggerAutoMatchLoading, true);

    const outcome = await runTask<boolean, TaskMeta>(
      async () => triggerBridgeMatching(),
      { type: TaskType.MATCH_BRIDGE_TRANSACTIONS, meta: { title: t('bridge_matching.auto_match.task_title') }, guard: false },
    );

    if (outcome.success) {
      await refreshUnmatchedBridgeTransactions(true);
      signalEventsModified();
    }
    else if (isActionableFailure(outcome)) {
      logger.error('Failed to trigger bridge auto match:', outcome.error);
      showErrorMessage(t('bridge_matching.auto_match.error_title'), t('bridge_matching.auto_match.error', { error: outcome.message }));
    }

    set(triggerAutoMatchLoading, false);
  };

  async function autoMatchBridgeTransaction(linkedTransaction: LinkedMovementMatch): Promise<boolean> {
    const { groupIdentifier, identifier, timeRange, tolerance } = linkedTransaction;
    const suggestions = await getBridgeMatches(groupIdentifier, timeRange, false, tolerance);
    if (suggestions.closeMatches.length > 0) {
      await matchBridgeTransactionsApi(identifier, suggestions.closeMatches);
      return true;
    }
    return false;
  }

  return {
    autoMatchBridgeTransaction,
    autoMatchLoading,
    autoMatchMinimumTier: bridgeMatchingMinimumTier,
    fetchUnmatchedBridgeTransactions,
    ignoredCount,
    ignoredLoading,
    ignoredTransactions,
    isAutoMatchAllowed: isBridgeMatchingAllowed,
    loading,
    matchBridgeTransaction,
    refreshUnmatchedBridgeTransactions,
    resolveExternal,
    triggerBridgeAutoMatching,
    unmatchedCount,
    unmatchedTransactions,
  };
});

/**
 * The bridge implementation of the shared matching flow contract, consumed by the
 * generic potential-matches components to search/link bridge counterpart events.
 */
export function useBridgeMatchingFlow(): MatchingFlow {
  const { getBridgeMatches } = useBridgeMatchingApi();
  const { matchBridgeTransaction, refreshUnmatchedBridgeTransactions } = useUnmatchedBridgeTransactions();
  const { bridgeMatchAmountTolerance, bridgeMatchTimeRange } = useBridgeMatchSettings();

  return {
    defaultTimeRangeSeconds: get(bridgeMatchTimeRange),
    defaultTolerance: get(bridgeMatchAmountTolerance),
    getSuggestions: getBridgeMatches,
    match: matchBridgeTransaction,
    refresh: refreshUnmatchedBridgeTransactions,
  };
}
