import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import { msg } from '@/message-key';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { UnmatchedVariant } from '@/modules/history/events/unmatched-row';
import { useAssetMovementActions } from '@/modules/history/events/use-asset-movement-actions';
import { type UnmatchedAssetMovement, useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { type UnmatchedMovementRow, useUnmatchedMovementRows } from '@/modules/history/events/use-unmatched-movement-rows';
import { useMovementUnmatchableExplanation } from '@/modules/history/events/use-untracked-movement-destination';
import { PinnedNames } from '@/modules/session/types';

/** Exchange deposits and withdrawals, matched against the on-chain side of the transfer. */
export const assetMovementMatchingKind: MatchingKind<UnmatchedAssetMovement, UnmatchedMovementRow> = {
  bulkSelection: { hideWhenEmpty: false, needsTier: true },
  getIdentifier: movement => getEventEntryFromCollection(movement.events).entry.identifier,
  messages: {
    actionFailed: msg.$t('asset_movement_matching.action_failed'),
    autoMatchTooltip: msg.$t('asset_movement_matching.actions.auto_match_tooltip'),
    title: msg.$t('asset_movement_matching.dialog.title'),
  },
  pinnedName: PinnedNames.MATCH_ASSET_MOVEMENTS,
  useActions: (options) => {
    const { confirmIgnoreAllFiat, fiatMovements, ignoreMovement, restoreMovement, ...actions } = useAssetMovementActions(options);
    return {
      ...actions,
      fiat: { confirmIgnoreAll: confirmIgnoreAllFiat, items: fiatMovements },
      ignore: ignoreMovement,
      restore: restoreMovement,
    };
  },
  useEntryLabels: () => computed<undefined>(() => undefined),
  useFlow: () => undefined,
  useRows: ({ items, ...options }) => useUnmatchedMovementRows({ ...options, movements: items }),
  useSource: () => {
    const { ignoredMovements, refreshUnmatchedAssetMovements, triggerAssetMovementAutoMatching, unmatchedMovements, ...source } = useUnmatchedAssetMovements();
    return {
      ...source,
      autoMatch: triggerAssetMovementAutoMatching,
      ignored: ignoredMovements,
      refresh: refreshUnmatchedAssetMovements,
      unmatched: unmatchedMovements,
    };
  },
  useUnmatchableExplanation: subject => useMovementUnmatchableExplanation(subject).unmatchableExplanation,
  variant: UnmatchedVariant.ASSET_MOVEMENT,
};
