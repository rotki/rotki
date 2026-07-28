import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { UNMATCHED_ACTIONS, type UnmatchedRowActionLabels, type UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import { getAssetMovementsType } from '@/modules/history/management/forms/utils';

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
 * The asset-movement surface's model. Movements have no counterpart to resolve, so their
 * spec is the same for every row - it is still built per row so the two surfaces answer the
 * same question the same way.
 */
export function useUnmatchedMovementRows(options: UseUnmatchedMovementRowsOptions): UseUnmatchedMovementRowsReturn {
  const { movements, showRestore, matchDisabled } = options;

  const { t } = useI18n({ useScope: 'global' });

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
      return {
        entry: eventEntry,
        eventSubtype: entry.eventSubtype,
        groupIdentifier: movement.groupIdentifier,
        isFiat: movement.isFiat,
        location: entry.location,
        original: movement,
        timestamp: entry.timestamp,
        typeLabel: getAssetMovementsType(entry.eventSubtype),
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

  function specFor(_row: UnmatchedMovementRow): UnmatchedRowActionSpec {
    return {
      confirms: {
        [UNMATCHED_ACTIONS.IGNORE]: {
          confirmLabel: t('asset_movement_matching.dialog.ignore'),
          message: t('asset_movement_matching.dialog.confirm_ignore'),
        },
      },
      labels: get(labels),
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
