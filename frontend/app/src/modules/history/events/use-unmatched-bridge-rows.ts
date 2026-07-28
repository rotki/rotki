import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { arrayify } from '@/modules/core/common/data/array';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { UNMATCHED_ACTIONS, type UnmatchedRowActionLabels, type UnmatchedRowActionSpec, type UnmatchedRowConfirms, type UnmatchedRowOptionalAction } from '@/modules/history/events/unmatched-actions';
import { canCreateBridgeCounterpart, getBridgeCounterpartAddress, isCounterpartUnqueryable, useUntrackedBridgeCounterpart } from '@/modules/history/events/use-untracked-bridge-counterpart';

/**
 * One unmatched bridge leg, with everything either presentation needs already decided.
 *
 * The wording lives on the row rather than in a helper each presentation calls, because a
 * helper is only shared until someone forgets: the dialog table rendered the raw
 * `deposit`/`withdrawal` for a while precisely because the card had its own label function.
 */
export interface UnmatchedBridgeRow {
  /** Row key: the leg event identifier, since a group can carry several bridge legs. */
  id: string;
  groupIdentifier: string;
  entry: HistoryEventEntry;
  direction: 'deposit' | 'withdrawal';
  directionLabel: string;
  location: string;
  timestamp: number;
  original: UnmatchedBridgeTransaction;
  counterpartAddress?: string;
  untrackedCounterpart: boolean;
  /** Names the untracked side ("Untracked destination"/"Untracked source"). */
  untrackedLabel: string;
  untrackedTooltip: string;
  canCreateCounterpart: boolean;
  unqueryableCounterpart: boolean;
}

interface UseUnmatchedBridgeRowsOptions {
  /** The legs to present, already filtered to unmatched or ignored by the caller. */
  transactions: MaybeRefOrGetter<UnmatchedBridgeTransaction[]>;
  /** The rows are ignored ones, so restore replaces the resolution actions. */
  showRestore: MaybeRefOrGetter<boolean | undefined>;
  /** Matching is unavailable (no premium tier), so find-match is offered but disabled. */
  matchDisabled: MaybeRefOrGetter<boolean | undefined>;
}

interface UseUnmatchedBridgeRowsReturn {
  rows: ComputedRef<UnmatchedBridgeRow[]>;
  description: ComputedRef<string>;
  emptyDescription: ComputedRef<string>;
  specFor: (row: UnmatchedBridgeRow) => UnmatchedRowActionSpec;
}

/**
 * The bridge surface's model: what the rows are, what they are called, and what may be done
 * to them. It has no notion of a table, a card or a pinned rail - the host picks a
 * presentation and both are handed the same rows and the same action specs.
 */
export function useUnmatchedBridgeRows(options: UseUnmatchedBridgeRowsOptions): UseUnmatchedBridgeRowsReturn {
  const { transactions, showRestore, matchDisabled } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { isCounterpartUntracked } = useUntrackedBridgeCounterpart();

  const labels = computed<UnmatchedRowActionLabels>(() => ({
    findMatch: t('asset_movement_matching.dialog.find_match'),
    findMatchAnyway: t('asset_movement_matching.dialog.find_match_anyway'),
    ignore: t('asset_movement_matching.dialog.ignore'),
    ignoreTooltip: t('bridge_matching.dialog.ignore_tooltip'),
    restore: t('asset_movement_matching.dialog.restore'),
    restoreTooltip: t('bridge_matching.dialog.restore_tooltip'),
    showInEventsTooltip: t('asset_movement_matching.dialog.show_in_events'),
  }));

  const rows = computed<UnmatchedBridgeRow[]>(() =>
    toValue(transactions).map((transaction) => {
      // Show the leg's own event: the row's collection can hold several events and the
      // first one is not necessarily the leg this row acts on.
      const { entry, ...meta } = arrayify(transaction.events).find(event => event.entry.identifier === transaction.identifier)
        ?? getEventEntryFromCollection(transaction.events);
      const eventEntry = { ...entry, ...meta };
      const ignored = !!toValue(showRestore);
      const untrackedCounterpart = !ignored && isCounterpartUntracked(transaction);
      const isDeposit = transaction.direction === 'deposit';
      const address = getBridgeCounterpartAddress(transaction);

      return {
        id: transaction.identifier.toString(),
        canCreateCounterpart: !ignored && canCreateBridgeCounterpart(transaction, untrackedCounterpart),
        counterpartAddress: address,
        direction: transaction.direction,
        directionLabel: isDeposit
          ? t('bridge_matching.dialog.direction_out')
          : t('bridge_matching.dialog.direction_in'),
        entry: eventEntry,
        groupIdentifier: transaction.groupIdentifier,
        location: entry.location,
        original: transaction,
        timestamp: entry.timestamp,
        unqueryableCounterpart: !ignored && isCounterpartUnqueryable(transaction),
        untrackedCounterpart,
        untrackedLabel: isDeposit
          ? t('bridge_matching.dialog.untracked_destination')
          : t('bridge_matching.dialog.untracked_source'),
        untrackedTooltip: isDeposit
          ? t('bridge_matching.dialog.untracked_destination_tooltip', { address: address ?? '' })
          : t('bridge_matching.dialog.untracked_source_tooltip', { address: address ?? '' }),
      };
    }),
  );

  const description = computed<string>(() =>
    toValue(showRestore)
      ? t('bridge_matching.dialog.ignored_description')
      : t('bridge_matching.dialog.description'),
  );

  const emptyDescription = computed<string>(() =>
    toValue(showRestore)
      ? t('bridge_matching.dialog.no_ignored')
      : t('bridge_matching.dialog.no_unmatched'),
  );

  /**
   * A known-untracked counterpart skips the confirm: external is the only correct outcome
   * there, and the undo notification still covers a misclick. Everything else asks in place.
   */
  function confirmsFor(row: UnmatchedBridgeRow): UnmatchedRowConfirms {
    const confirms: UnmatchedRowConfirms = {
      [UNMATCHED_ACTIONS.IGNORE]: {
        confirmLabel: t('asset_movement_matching.dialog.ignore'),
        message: t('bridge_matching.dialog.confirm_ignore'),
      },
    };

    if (!row.untrackedCounterpart) {
      confirms[UNMATCHED_ACTIONS.MARK_EXTERNAL] = {
        confirmLabel: t('bridge_matching.dialog.mark_external'),
        message: t('bridge_matching.dialog.confirm_mark_external'),
      };
    }

    return confirms;
  }

  function markExternalFor(row: UnmatchedBridgeRow): UnmatchedRowOptionalAction {
    return {
      emphasize: row.untrackedCounterpart && !row.unqueryableCounterpart,
      label: t('bridge_matching.dialog.mark_external'),
      tooltip: row.direction === 'deposit'
        ? t('bridge_matching.dialog.mark_external_tooltip')
        : t('bridge_matching.dialog.mark_external_in_tooltip'),
    };
  }

  function createCounterpartFor(row: UnmatchedBridgeRow): UnmatchedRowOptionalAction | undefined {
    if (!row.canCreateCounterpart)
      return undefined;

    return {
      emphasize: row.unqueryableCounterpart,
      label: t('bridge_matching.dialog.create_counterpart'),
      tooltip: row.direction === 'deposit'
        ? t('bridge_matching.dialog.create_counterpart_tooltip')
        : t('bridge_matching.dialog.create_counterpart_in_tooltip'),
    };
  }

  function specFor(row: UnmatchedBridgeRow): UnmatchedRowActionSpec {
    return {
      confirms: confirmsFor(row),
      createCounterpart: createCounterpartFor(row),
      labels: get(labels),
      markExternal: markExternalFor(row),
      matchDisabled: !!toValue(matchDisabled),
      showRestore: !!toValue(showRestore),
    };
  }

  return {
    description,
    emptyDescription,
    rows,
    specFor,
  };
}
