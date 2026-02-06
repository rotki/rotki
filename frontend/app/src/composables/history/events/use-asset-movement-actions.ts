import type { ComputedRef, Ref } from 'vue';
import { useAssetMovementMatchingApi } from '@/composables/api/history/events/asset-movement-matching';
import { type UnmatchedAssetMovement, useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import { useConfirmStore } from '@/store/confirm';
import { getEventEntryFromCollection } from '@/utils/history/events';

interface UseAssetMovementActionsOptions {
  onActionComplete?: () => Promise<void>;
}

interface UseAssetMovementActionsReturn {
  fiatMovements: ComputedRef<UnmatchedAssetMovement[]>;
  ignoreLoading: Ref<boolean>;
  selectedIgnored: Ref<string[]>;
  selectedUnmatched: Ref<string[]>;
  confirmIgnoreAllFiat: () => void;
  confirmIgnoreSelected: () => void;
  confirmRestoreSelected: () => void;
  ignoreMovement: (movement: UnmatchedAssetMovement) => Promise<void>;
  restoreMovement: (movement: UnmatchedAssetMovement) => Promise<void>;
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
  } = useUnmatchedAssetMovements();

  const { matchAssetMovements, unlinkAssetMovement } = useAssetMovementMatchingApi();
  const { show } = useConfirmStore();

  const ignoreLoading = ref<boolean>(false);
  const selectedUnmatched = ref<string[]>([]);
  const selectedIgnored = ref<string[]>([]);

  const fiatMovements = computed<UnmatchedAssetMovement[]>(() =>
    get(unmatchedMovements).filter(movement => movement.isFiat),
  );

  function getMovementIdentifier(movement: UnmatchedAssetMovement): number {
    return getEventEntryFromCollection(movement.events).entry.identifier;
  }

  async function ignoreMovement(movement: UnmatchedAssetMovement): Promise<void> {
    set(ignoreLoading, true);
    try {
      await matchAssetMovements(getMovementIdentifier(movement));
      await refreshUnmatchedAssetMovements();
      await onActionComplete?.();
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function restoreMovement(movement: UnmatchedAssetMovement): Promise<void> {
    set(ignoreLoading, true);
    try {
      await unlinkAssetMovement(getMovementIdentifier(movement));
      await refreshUnmatchedAssetMovements();
      await onActionComplete?.();
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function ignoreSelectedMovements(groupIdentifiers: string[]): Promise<void> {
    set(ignoreLoading, true);
    try {
      const movements = get(unmatchedMovements).filter(m => groupIdentifiers.includes(m.groupIdentifier));
      for (const movement of movements)
        await matchAssetMovements(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(selectedUnmatched, []);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function unignoreSelectedMovements(groupIdentifiers: string[]): Promise<void> {
    set(ignoreLoading, true);
    try {
      const movements = get(ignoredMovements).filter(m => groupIdentifiers.includes(m.groupIdentifier));
      for (const movement of movements)
        await unlinkAssetMovement(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(selectedIgnored, []);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function confirmIgnoreSelected(): void {
    const count = get(selectedUnmatched).length;
    show({
      message: t('asset_movement_matching.actions.ignore_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('asset_movement_matching.actions.ignore_selected'),
    }, async () => ignoreSelectedMovements(get(selectedUnmatched)));
  }

  function confirmRestoreSelected(): void {
    const count = get(selectedIgnored).length;
    show({
      message: t('asset_movement_matching.actions.restore_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('asset_movement_matching.actions.restore_selected'),
    }, async () => unignoreSelectedMovements(get(selectedIgnored)));
  }

  async function ignoreAllFiatMovements(): Promise<void> {
    set(ignoreLoading, true);
    try {
      for (const movement of get(fiatMovements))
        await matchAssetMovements(getMovementIdentifier(movement));

      await refreshUnmatchedAssetMovements();
      set(selectedUnmatched, []);
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
    confirmIgnoreAllFiat,
    confirmIgnoreSelected,
    confirmRestoreSelected,
    fiatMovements,
    ignoreLoading,
    ignoreMovement,
    restoreMovement,
    selectedIgnored,
    selectedUnmatched,
  };
}
