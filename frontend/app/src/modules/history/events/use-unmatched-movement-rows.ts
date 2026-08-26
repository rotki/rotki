import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { HistoryEventEntryType } from '@rotki/common';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { UNMATCHED_ACTIONS, type UnmatchedRowActionLabels, type UnmatchedRowActionSpec, type UnmatchedRowConfirms, type UnmatchedRowOptionalAction } from '@/modules/history/events/unmatched-actions';
import { getMovementDestinationAddress, useUntrackedMovementDestination } from '@/modules/history/events/use-untracked-movement-destination';
import { getAssetMovementsType } from '@/modules/history/management/forms/utils';

/**
 * The backend's own record of having resolved a movement as external, if this event carries one.
 *
 * @param entry - the movement's own event, resolved or not
 * @returns the stamp, or `undefined` for anything the backend did not resolve
 */
function externalResolution(entry: HistoryEventEntry): { direction?: string | null } | undefined {
  if (entry.entryType !== HistoryEventEntryType.HISTORY_EVENT)
    return undefined;

  const stamp = entry.extraData?.matchedAssetMovement;
  return stamp?.resolution === 'external' ? stamp : undefined;
}

/**
 * Which way the funds moved.
 *
 * @remarks
 * An asset movement says so in its subtype. One resolved as external is no longer an asset movement
 * at all and kept the same subtype for either direction (`payment`), so its direction is read from
 * the stamp the backend wrote for exactly this purpose rather than inferred from its event type.
 *
 * @param entry - the movement's own event, resolved or not
 * @returns `deposit` when the funds arrived on the exchange, `withdrawal` when they left it
 */
function movementDirection(entry: HistoryEventEntry): 'deposit' | 'withdrawal' {
  const resolution = externalResolution(entry);
  if (resolution)
    return resolution.direction === 'deposit' ? 'deposit' : 'withdrawal';

  return getAssetMovementsType(entry.eventSubtype);
}

/** One unmatched asset movement, with its wording already decided. See [[UnmatchedBridgeRow]]. */
export interface UnmatchedMovementRow {
  /** Row key: a movement is matched as a whole group, unlike a bridge leg. */
  groupIdentifier: string;
  entry: HistoryEventEntry;
  eventSubtype: string;
  typeLabel: string;
  isFiat: boolean;
  location: string;
  timestamp: number;
  original: UnmatchedAssetMovement;
  /** A withdrawal is resolved as a payment out, a deposit as income. */
  direction: 'deposit' | 'withdrawal';
  destinationAddress?: string;
  /** Only ever true for a withdrawal - see {@link getMovementDestinationAddress}. */
  untrackedDestination: boolean;
  untrackedLabel: string;
  untrackedTooltip: string;
  /** The row was already resolved as a payment or as income, rather than merely ignored. */
  resolvedAsExternal: boolean;
  resolvedLabel: string;
}

interface UseUnmatchedMovementRowsOptions {
  /** The movements to present, already filtered to unmatched or ignored by the caller. */
  movements: MaybeRefOrGetter<UnmatchedAssetMovement[]>;
  /** The rows are ignored ones, so restore replaces the resolution actions. */
  showRestore: MaybeRefOrGetter<boolean | undefined>;
  /** Matching is unavailable (no premium tier), so find-match is offered but disabled. */
  matchDisabled: MaybeRefOrGetter<boolean | undefined>;
}

interface UseUnmatchedMovementRowsReturn {
  rows: ComputedRef<UnmatchedMovementRow[]>;
  description: ComputedRef<string>;
  emptyDescription: ComputedRef<string>;
  specFor: (row: UnmatchedMovementRow) => UnmatchedRowActionSpec;
}

/**
 * The asset-movement surface's model: what the rows are, what they are called, and what may
 * be done to them. It has no notion of a table, a card or a pinned rail - the host picks a
 * presentation and both are handed the same rows and the same action specs.
 */
export function useUnmatchedMovementRows(options: UseUnmatchedMovementRowsOptions): UseUnmatchedMovementRowsReturn {
  const { movements, showRestore, matchDisabled } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { isDestinationUntracked } = useUntrackedMovementDestination();

  const labels = computed<UnmatchedRowActionLabels>(() => ({
    findMatch: t('asset_movement_matching.dialog.find_match'),
    findMatchAnyway: t('asset_movement_matching.dialog.find_match_anyway'),
    ignore: t('asset_movement_matching.dialog.ignore'),
    ignoreTooltip: t('asset_movement_matching.dialog.ignore_tooltip'),
    restore: t('asset_movement_matching.dialog.restore'),
    restoreTooltip: t('asset_movement_matching.dialog.restore_tooltip'),
    showInEventsTooltip: t('asset_movement_matching.dialog.show_in_events'),
  }));

  const rows = computed<UnmatchedMovementRow[]>(() =>
    toValue(movements).map((movement) => {
      const { entry, ...meta } = getEventEntryFromCollection(movement.events);
      const eventEntry = { ...entry, ...meta };
      const ignored = !!toValue(showRestore);
      const address = getMovementDestinationAddress(eventEntry);
      const direction = movementDirection(eventEntry);
      const resolvedAsExternal = externalResolution(eventEntry) !== undefined;
      return {
        destinationAddress: address,
        direction,
        entry: eventEntry,
        eventSubtype: entry.eventSubtype,
        groupIdentifier: movement.groupIdentifier,
        isFiat: movement.isFiat,
        location: entry.location,
        original: movement,
        resolvedAsExternal,
        resolvedLabel: direction === 'deposit'
          ? t('asset_movement_matching.dialog.resolved_income')
          : t('asset_movement_matching.dialog.resolved_payment'),
        timestamp: entry.timestamp,
        typeLabel: direction,
        untrackedDestination: !ignored && isDestinationUntracked(eventEntry),
        untrackedLabel: t('asset_movement_matching.dialog.untracked_destination'),
        untrackedTooltip: t('asset_movement_matching.dialog.untracked_destination_tooltip', { address: address ?? '' }),
      };
    }),
  );

  const description = computed<string>(() =>
    toValue(showRestore)
      ? t('asset_movement_matching.dialog.ignored_description')
      : t('asset_movement_matching.dialog.description'),
  );

  const emptyDescription = computed<string>(() =>
    toValue(showRestore)
      ? t('asset_movement_matching.dialog.no_ignored')
      : t('asset_movement_matching.dialog.no_unmatched'),
  );

  /**
   * What the row asks before it acts.
   *
   * @remarks
   * A verified untracked destination has only one correct outcome, so it does not ask at all.
   * Everywhere else it asks about the outcome that direction actually produces: one message about
   * a payment either way misdescribes half of what is being confirmed.
   *
   * @param row - the row the actions belong to
   * @returns the confirms by action; anything absent runs on click
   */
  function confirmsFor(row: UnmatchedMovementRow): UnmatchedRowConfirms {
    const confirms: UnmatchedRowConfirms = {
      [UNMATCHED_ACTIONS.IGNORE]: {
        confirmLabel: t('asset_movement_matching.dialog.ignore'),
        message: t('asset_movement_matching.dialog.confirm_ignore'),
      },
    };

    if (!row.untrackedDestination) {
      confirms[UNMATCHED_ACTIONS.MARK_EXTERNAL] = {
        confirmLabel: t('asset_movement_matching.dialog.mark_external'),
        message: row.direction === 'withdrawal'
          ? t('asset_movement_matching.dialog.confirm_mark_external')
          : t('asset_movement_matching.dialog.confirm_mark_external_in'),
      };
    }

    return confirms;
  }

  function markExternalFor(row: UnmatchedMovementRow): UnmatchedRowOptionalAction {
    return {
      emphasize: row.untrackedDestination,
      label: t('asset_movement_matching.dialog.mark_external'),
      tooltip: row.direction === 'withdrawal'
        ? t('asset_movement_matching.dialog.mark_external_tooltip')
        : t('asset_movement_matching.dialog.mark_external_in_tooltip'),
    };
  }

  function specFor(row: UnmatchedMovementRow): UnmatchedRowActionSpec {
    return {
      confirms: confirmsFor(row),
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
