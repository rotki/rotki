import type { ComputedRef, Ref } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
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
  confirmIgnoreAllFiat: () => void;
  confirmIgnoreSelected: () => void;
  confirmRestoreSelected: () => void;
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
  const { show } = useConfirmStore();

  const ignoreLoading = shallowRef<boolean>(false);
  const actionFailure = shallowRef<unknown>();
  const modelSelectedUnmatched = ref<string[]>([]);
  const modelSelectedIgnored = ref<string[]>([]);
  const notice = shallowRef<MovementResolutionNotice>();

  const fiatMovements = computed<UnmatchedAssetMovement[]>(() =>
    get(unmatchedMovements).filter(movement => movement.isFiat),
  );

  /** Keeps a failed action for the panel to name, and logs it. */
  function reportFailure(error: unknown): void {
    logger.error('Failed to update an unmatched asset movement:', error);
    set(actionFailure, error);
  }

  function getMovementIdentifier(movement: UnmatchedAssetMovement): number {
    return getEventEntryFromCollection(movement.events).entry.identifier;
  }

  async function ignoreMovement(movement: UnmatchedAssetMovement): Promise<void> {
    set(ignoreLoading, true);
    set(actionFailure, undefined);
    try {
      await matchAssetMovements(getMovementIdentifier(movement));
      await refreshUnmatchedAssetMovements();
      await onActionComplete?.();
    }
    catch (error: unknown) {
      reportFailure(error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function restoreMovement(movement: UnmatchedAssetMovement): Promise<void> {
    set(ignoreLoading, true);
    set(actionFailure, undefined);
    try {
      await unlinkAssetMovement(getMovementIdentifier(movement));
      if (get(notice)?.movement.groupIdentifier === movement.groupIdentifier)
        dismissResolution();

      await refreshUnmatchedAssetMovements();
      await onActionComplete?.();
    }
    catch (error: unknown) {
      reportFailure(error);
    }
    finally {
      set(ignoreLoading, false);
    }
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
    set(ignoreLoading, true);
    set(actionFailure, undefined);
    try {
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
    }
    catch (error: unknown) {
      reportFailure(error);
    }
    finally {
      set(ignoreLoading, false);
    }
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
    set(ignoreLoading, true);
    set(actionFailure, undefined);
    try {
      const movements = get(unmatchedMovements).filter(m => groupIdentifiers.includes(m.groupIdentifier));
      for (const movement of movements)
        await matchAssetMovements(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(modelSelectedUnmatched, []);
    }
    catch (error: unknown) {
      reportFailure(error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function unignoreSelectedMovements(groupIdentifiers: string[]): Promise<void> {
    set(ignoreLoading, true);
    set(actionFailure, undefined);
    try {
      const movements = get(ignoredMovements).filter(m => groupIdentifiers.includes(m.groupIdentifier));
      for (const movement of movements)
        await unlinkAssetMovement(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(modelSelectedIgnored, []);
    }
    catch (error: unknown) {
      reportFailure(error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function confirmIgnoreSelected(): void {
    const count = get(modelSelectedUnmatched).length;
    show({
      message: t('asset_movement_matching.actions.ignore_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('asset_movement_matching.actions.ignore_selected'),
    }, async () => ignoreSelectedMovements(get(modelSelectedUnmatched)));
  }

  function confirmRestoreSelected(): void {
    const count = get(modelSelectedIgnored).length;
    show({
      message: t('asset_movement_matching.actions.restore_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('asset_movement_matching.actions.restore_selected'),
    }, async () => unignoreSelectedMovements(get(modelSelectedIgnored)));
  }

  async function ignoreAllFiatMovements(): Promise<void> {
    set(ignoreLoading, true);
    set(actionFailure, undefined);
    try {
      for (const movement of get(fiatMovements))
        await matchAssetMovements(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(modelSelectedUnmatched, []);
    }
    catch (error: unknown) {
      reportFailure(error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function confirmIgnoreAllFiat(): void {
    const count = get(fiatMovements).length;
    show({
      message: t('asset_movement_matching.actions.ignore_fiat_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('asset_movement_matching.actions.ignore_fiat'),
    }, async () => ignoreAllFiatMovements());
  }

  return {
    actionFailure: shallowReadonly(actionFailure),
    confirmIgnoreAllFiat,
    confirmIgnoreSelected,
    confirmRestoreSelected,
    dismissResolution,
    fiatMovements,
    ignoreLoading: readonly(ignoreLoading),
    ignoreMovement,
    markExternal,
    restoreMovement,
    modelSelectedIgnored,
    modelSelectedUnmatched,
    resolutionNotice: shallowReadonly(notice),
    undoResolution,
  };
}
