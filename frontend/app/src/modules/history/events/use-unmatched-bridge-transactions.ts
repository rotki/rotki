import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { LinkedMovementMatch } from '@/modules/history/events/event-payloads';
import type { MatchingFlow, UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { HistoryEventCollectionRow, HistoryEventEntryWithMeta } from '@/modules/history/events/schemas';
import { NotificationGroup } from '@rotki/common';
import { isErr, map as mapResult } from 'plainfp/result';
import { z } from 'zod';
import { arrayify } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useBridgeMatchingApi } from '@/modules/history/api/events/use-bridge-matching-api';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useBridgeMatchSettings } from '@/modules/settings/use-bridge-match-settings';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, isActionable, makeActivityId, type TaskOutcome, useNativeTask } from '@/modules/task-center/use-native-task';

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
 * Reads back the original direction of a bridge leg that was resolved as external.
 *
 * @remarks
 * Resolution turns the event into a plain spend/receive, so the direction has to come from this
 * stamp rather than from the event type.
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
  identifier: number;
  direction: 'deposit' | 'withdrawal';
  bridge?: BridgeExtraData;
}

interface BridgeEntryMatch {
  event: HistoryEventEntryWithMeta;
  row: HistoryEventCollectionRow;
}

/**
 * Locates a bridge leg's event across the fetched rows by its identifier. The backend
 * reports unresolved legs per event, and the exact event has to be acted on: a
 * transaction can carry more than one bridge leg (e.g. several bridged assets in one
 * transaction), so picking a leg positionally or by type heuristics would act on the
 * wrong leg, possibly one that is already ignored.
 */
function findBridgeEntry(rows: HistoryEventCollectionRow[], identifier: number): BridgeEntryMatch | undefined {
  for (const row of rows) {
    const event = arrayify(row).find(({ entry }) => entry.identifier === identifier);
    if (event)
      return { event, row };
  }
  return undefined;
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
  resolveCreateCounterpart: (bridgeEventId: number) => Promise<ActionStatus>;
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
  const { statusOf, submitTask, useIsActive } = useNativeTask();

  const { fetchHistoryEvents } = useHistoryEventsApi();
  const {
    getBridgeMatches,
    getUnmatchedBridgeTransactions,
    matchBridgeTransactions: matchBridgeTransactionsApi,
    triggerBridgeMatching,
  } = useBridgeMatchingApi();
  const { signalEventsModified } = useHistoryStore();
  const { allowed: isBridgeMatchingAllowed, minimumTier: bridgeMatchingMinimumTier } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

  const autoMatchLoading = logicOr(triggerAutoMatchLoading, useIsActive(ActivityKind.HISTORY_EVENTS, ActivityPart.BRIDGE));

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
      const legs = await getUnmatchedBridgeTransactions(onlyIgnored);

      if (legs.length === 0) {
        set(transactionsRef, []);
        if (!isIgnored)
          clearUnmatchedBridgeTransactionsNotification();
        return;
      }

      const response = await fetchHistoryEvents({
        aggregateByGroupIds: false,
        groupIdentifiers: [...new Set(legs.map(leg => leg.groupIdentifier))],
        limit: -1,
        offset: 0,
        orderByAttributes: ['timestamp'],
        ascending: [false],
      });

      const transactions: UnmatchedBridgeTransaction[] = [];

      for (const leg of legs) {
        const bridgeMatch = findBridgeEntry(response.entries, leg.identifier);

        if (!bridgeMatch) {
          logger.warn(`No event found for bridge leg ${leg.identifier} in group ${leg.groupIdentifier}, skipping it`);
          continue;
        }

        const entry = bridgeMatch.event.entry;
        const extraData = 'extraData' in entry ? entry.extraData : undefined;

        transactions.push({
          asset: entry.asset,
          bridge: getBridgeExtraData(extraData),
          direction: deriveBridgeDirection(extraData, entry.eventType),
          events: bridgeMatch.row,
          groupIdentifier: leg.groupIdentifier,
          identifier: leg.identifier,
        });
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
      const success = await matchBridgeTransactionsApi(bridgeEventId, undefined, 'external');

      if (success) {
        // the caller reports this with an undo affordance, so no success dialog here
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

  const resolveCreateCounterpart = async (bridgeEventId: number): Promise<ActionStatus> => {
    try {
      const success = await matchBridgeTransactionsApi(bridgeEventId, undefined, 'createCounterpart');

      if (success) {
        showSuccessMessage(t('actions.bridge_matching.create_counterpart_success.title'), t('actions.bridge_matching.create_counterpart_success.description'));
        signalEventsModified();
      }

      return { message: '', success };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      logger.error('Failed to create the counterpart of a bridge transaction:', error);
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
    if (!get(isBridgeMatchingAllowed) || statusOf(ActivityKind.HISTORY_EVENTS, ActivityPart.BRIDGE).active)
      return;

    set(triggerAutoMatchLoading, true);

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.HISTORY_EVENTS, ActivityPart.BRIDGE),
      kind: ActivityKind.HISTORY_EVENTS,
      rerunnable: true,
      run: async ({ runTask }): Promise<TaskOutcome> => mapResult(
        await runTask<boolean>(
          async () => triggerBridgeMatching(),
        ),
        () => {},
      ),
      subtitle: activityLabel(ActivityKind.HISTORY_EVENTS, ActivityPart.BRIDGE),
      title: t('task_center.group.history_events'),
    });

    if (!isErr(outcome)) {
      await refreshUnmatchedBridgeTransactions(true);
      signalEventsModified();
    }
    else if (isActionable(outcome.error)) {
      logger.error('Failed to trigger bridge auto match:', outcome.error);
      showErrorMessage(t('bridge_matching.auto_match.error_title'), t('bridge_matching.auto_match.error', { error: outcome.error.message }));
    }

    set(triggerAutoMatchLoading, false);
  };

  async function autoMatchBridgeTransaction(linkedTransaction: LinkedMovementMatch): Promise<boolean> {
    const { identifier, timeRange, tolerance } = linkedTransaction;
    const suggestions = await getBridgeMatches(identifier, timeRange, false, tolerance);
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
    resolveCreateCounterpart,
    resolveExternal,
    triggerBridgeAutoMatching,
    unmatchedCount,
    unmatchedTransactions,
  };
});

export interface BridgeEntryLabels {
  type: string;
  locationHeader: string;
  matchingFor: string;
}

/**
 * How a bridge leg describes itself inside the generic matching UI. Shared by the dialog
 * and the pinned panel so the two cannot drift apart on wording.
 */
export function useBridgeEntryLabels(
  transaction: MaybeRefOrGetter<UnmatchedBridgeTransaction | undefined>,
): ComputedRef<BridgeEntryLabels> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<BridgeEntryLabels>(() => {
    const isDeposit = toValue(transaction)?.direction !== 'withdrawal';
    return {
      locationHeader: t('common.location'),
      // the generic copy calls every subject an "asset movement", which a bridge leg is not
      matchingFor: isDeposit
        ? t('bridge_matching.dialog.matching_for_out')
        : t('bridge_matching.dialog.matching_for_in'),
      type: isDeposit
        ? t('bridge_matching.dialog.direction_out')
        : t('bridge_matching.dialog.direction_in'),
    };
  });
}

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
    getSuggestions: async (movement, timeRangeSeconds, onlyExpectedAssets, tolerance) => getBridgeMatches(
      movement.identifier ?? getEventEntryFromCollection(movement.events).entry.identifier,
      timeRangeSeconds,
      onlyExpectedAssets,
      tolerance,
    ),
    match: matchBridgeTransaction,
    refresh: refreshUnmatchedBridgeTransactions,
  };
}
