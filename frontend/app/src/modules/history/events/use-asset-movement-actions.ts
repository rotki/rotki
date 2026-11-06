import type { ComputedRef, Ref } from 'vue';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { logger } from '@/modules/core/common/logging/logging';
import { useAssetMovementMatchingApi } from '@/modules/history/api/events/use-asset-movement-matching-api';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { type UnmatchedAssetMovement, useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { getAssetMovementsType } from '@/modules/history/management/forms/utils';

interface UseAssetMovementActionsOptions {
  /** Awaited after a single movement is ignored or restored (not after the bulk actions), letting the caller refresh its own view. */
  onActionComplete?: () => Promise<void>;
}

/**
 * What the panel says about the resolution the user just made, and the movement an undo
 * would restore. The wording is decided here rather than by the presentation, since it
 * depends on the direction: a resolved withdrawal is a payment out, a resolved deposit is
 * income.
 */
interface MovementResolutionNotice {
  message: string;
  movement: UnmatchedAssetMovement;
}

interface UseAssetMovementActionsReturn {
  fiatMovements: ComputedRef<UnmatchedAssetMovement[]>;
  ignoreLoading: Readonly<Ref<boolean>>;
  /**
   * Why the last action on a movement failed, for the panel to name beside the list it changed.
   * Cleared when the next action starts.
   */
  actionFailure: Readonly<Ref<unknown>>;
  modelSelectedIgnored: Ref<string[]>;
  modelSelectedUnmatched: Ref<string[]>;
  resolutionNotice: Readonly<Ref<MovementResolutionNotice | undefined>>;
  /** Ignores every fiat movement, once its button asked. */
  ignoreAllFiat: () => Promise<void>;
  /** What ignoring every fiat movement asks beside its button, counting them. */
  ignoreFiatQuestion: ComputedRef<ConfirmQuestion>;
  /** Ignores the selected movements, once their button asked. */
  ignoreSelected: () => Promise<void>;
  /** What ignoring the selection asks beside its button, counting the selected movements. */
  ignoreSelectedQuestion: ComputedRef<ConfirmQuestion>;
  restoreSelected: () => Promise<void>;
  dismissResolution: () => void;
  ignoreMovement: (movement: UnmatchedAssetMovement) => Promise<void>;
  markExternal: (movement: UnmatchedAssetMovement) => Promise<void>;
  restoreMovement: (movement: UnmatchedAssetMovement) => Promise<void>;
  undoResolution: () => Promise<void>;
}

export function useAssetMovementActions(
  options: UseAssetMovementActionsOptions = {},
): UseAssetMovementActionsReturn {
  const { onActionComplete } = options;

  const { t } = useI18n({ useScope: 'global' });

  const {
    ignoredMovements,
    unmatchedMovements,
    refreshUnmatchedAssetMovements,
    resolveExternal,
  } = useUnmatchedAssetMovements();

  const { matchAssetMovements, unlinkAssetMovement } = useAssetMovementMatchingApi();

  const ignoreLoading = shallowRef<boolean>(false);
  const actionFailure = shallowRef<unknown>();
  const modelSelectedUnmatched = ref<string[]>([]);
  const modelSelectedIgnored = ref<string[]>([]);
  const notice = shallowRef<MovementResolutionNotice>();

  const fiatMovements = computed<UnmatchedAssetMovement[]>(() =>
    get(unmatchedMovements).filter(movement => movement.isFiat),
  );

  /** Runs an action behind the loading flag, keeping its failure for the panel to name until the next one starts. */
  async function runAction(action: () => Promise<void>): Promise<void> {
    set(ignoreLoading, true);
    set(actionFailure, undefined);
    try {
      await action();
    }
    catch (error: unknown) {
      logger.error('Failed to update an unmatched asset movement:', error);
      set(actionFailure, error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function getMovementIdentifier(movement: UnmatchedAssetMovement): number {
    return getEventEntryFromCollection(movement.events).entry.identifier;
  }

  async function ignoreMovement(movement: UnmatchedAssetMovement): Promise<void> {
    await runAction(async () => {
      await matchAssetMovements(getMovementIdentifier(movement));
      await refreshUnmatchedAssetMovements();
      await onActionComplete?.();
    });
  }

  async function restoreMovement(movement: UnmatchedAssetMovement): Promise<void> {
    await runAction(async () => {
      await unlinkAssetMovement(getMovementIdentifier(movement));
      if (get(notice)?.movement.groupIdentifier === movement.groupIdentifier)
        dismissResolution();

      await refreshUnmatchedAssetMovements();
      await onActionComplete?.();
    });
  }

  /**
   * Resolves a movement whose counterpart is not tracked: a withdrawal becomes a payment and
   * a deposit becomes income, so the whole amount is accounted rather than just the fee.
   *
   * @remarks
   * Like ignoring, this is undone by the same unlink call the Restore action uses, so it reports
   * itself with an undo affordance in the panel it was triggered from instead of asking first with
   * a modal. Only the latest resolution is held, which costs nothing durable: the movement also
   * lands in the ignored tab and keeps a Restore there long after the notice is gone.
   *
   * @param movement - the movement to resolve; a rejected resolution leaves no notice behind
   */
  async function markExternal(movement: UnmatchedAssetMovement): Promise<void> {
    await runAction(async () => {
      const result = await resolveExternal(getMovementIdentifier(movement));
      if (result.success) {
        await refreshUnmatchedAssetMovements();
        await onActionComplete?.();
        set(notice, {
          message: getAssetMovementsType(getEventEntryFromCollection(movement.events).entry.eventSubtype) === 'deposit'
            ? t('asset_movement_matching.resolved.external_deposit')
            : t('asset_movement_matching.resolved.external_withdrawal'),
          movement,
        });
      }
      else {
        set(actionFailure, result.message);
      }
    });
  }

  function dismissResolution(): void {
    set(notice, undefined);
  }

  async function undoResolution(): Promise<void> {
    const current = get(notice);
    if (current)
      await restoreMovement(current.movement);
  }

  async function ignoreSelectedMovements(groupIdentifiers: string[]): Promise<void> {
    await runAction(async () => {
      const movements = get(unmatchedMovements).filter(m => groupIdentifiers.includes(m.groupIdentifier));
      for (const movement of movements)
        await matchAssetMovements(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(modelSelectedUnmatched, []);
    });
  }

  async function unignoreSelectedMovements(groupIdentifiers: string[]): Promise<void> {
    await runAction(async () => {
      const movements = get(ignoredMovements).filter(m => groupIdentifiers.includes(m.groupIdentifier));
      for (const movement of movements)
        await unlinkAssetMovement(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(modelSelectedIgnored, []);
    });
  }

  const ignoreSelectedQuestion = computed<ConfirmQuestion>(() => ({
    confirmLabel: t('asset_movement_matching.dialog.ignore'),
    message: t('asset_movement_matching.actions.ignore_selected_confirm', { count: get(modelSelectedUnmatched).length }),
    title: t('asset_movement_matching.actions.ignore_selected'),
  }));

  async function ignoreSelected(): Promise<void> {
    await ignoreSelectedMovements(get(modelSelectedUnmatched));
  }

  /** Restores the selection without asking: ignoring them again is the undo. */
  async function restoreSelected(): Promise<void> {
    await unignoreSelectedMovements(get(modelSelectedIgnored));
  }

  async function ignoreAllFiat(): Promise<void> {
    await runAction(async () => {
      for (const movement of get(fiatMovements))
        await matchAssetMovements(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(modelSelectedUnmatched, []);
    });
  }

  const ignoreFiatQuestion = computed<ConfirmQuestion>(() => ({
    confirmLabel: t('asset_movement_matching.dialog.ignore'),
    message: t('asset_movement_matching.actions.ignore_fiat_confirm', { count: get(fiatMovements).length }),
    title: t('asset_movement_matching.actions.ignore_fiat'),
  }));

  return {
    actionFailure: shallowReadonly(actionFailure),
    dismissResolution,
    fiatMovements,
    ignoreAllFiat,
    ignoreFiatQuestion,
    ignoreLoading: readonly(ignoreLoading),
    ignoreSelected,
    ignoreSelectedQuestion,
    ignoreMovement,
    markExternal,
    restoreMovement,
    restoreSelected,
    modelSelectedIgnored,
    modelSelectedUnmatched,
    resolutionNotice: shallowReadonly(notice),
    undoResolution,
  };
}
