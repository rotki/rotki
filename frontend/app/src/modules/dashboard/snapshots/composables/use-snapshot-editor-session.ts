import type { Snapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, Zero } from '@rotki/common';
import { useEventListener } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, readonly, type Ref, ref, shallowRef, toValue, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { onBeforeRouteLeave, useRouter } from 'vue-router';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirm } from '@/modules/core/common/use-confirm';
import { useSnapshotDraft } from '@/modules/dashboard/snapshots/composables/use-snapshot-draft';
import { useSnapshotStore } from '@/modules/dashboard/snapshots/use-snapshot-store';
import { getTotalValue } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

type SnapshotDraft = ReturnType<typeof useSnapshotDraft>;

interface UseSnapshotEditorSessionOptions {
  /** The timestamp, in seconds, of the snapshot being edited; a change loads that snapshot. */
  timestamp: MaybeRefOrGetter<number>;
  /** Re-pulls the net-value series after a save or a delete, so every reader of it sees the change. */
  refreshNetValue: () => Promise<void>;
}

interface UseSnapshotEditorSessionReturn extends SnapshotDraft {
  /** Whether the first snapshot is loading; a later navigation keeps the loaded one on screen. */
  loading: Readonly<Ref<boolean>>;
  /** Whether a save is in flight. */
  saving: Readonly<Ref<boolean>>;
  /** Why the snapshot could not be loaded, if it could not. */
  loadError: Readonly<Ref<string | undefined>>;
  /** Why the last save or delete failed; the template clears it. */
  modelActionError: Ref<string | undefined>;
  /** Whether the last save went through; the template clears it. */
  modelSaveSuccess: Ref<boolean>;
  /** The draft's net worth, zero until it loads. */
  netWorth: ComputedRef<BigNumber>;
  /** Persists the draft, marks its queued spam assets, and re-pulls the net-value series. */
  save: () => Promise<void>;
  /** Deletes the snapshot and leaves for the snapshot list once it is gone. */
  performDelete: () => Promise<void>;
}

/**
 * Loads, edits, saves and deletes one snapshot, and guards leaving it with unsaved edits.
 *
 * @remarks
 * Registers the route-leave guard and the `beforeunload` listener of the calling component, so it
 * must be called from a component's setup.
 */
export function useSnapshotEditorSession(options: UseSnapshotEditorSessionOptions): UseSnapshotEditorSessionReturn {
  const { refreshNetValue, timestamp } = options;
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();

  const loading = shallowRef<boolean>(true);
  const saving = shallowRef<boolean>(false);
  const loadError = shallowRef<string>();
  const modelActionError = shallowRef<string>();
  const modelSaveSuccess = shallowRef<boolean>(false);
  const loaded = ref<Snapshot>();

  const { fetchSnapshot, persist, remove } = useSnapshotStore();
  const { ask } = useConfirm();
  const { markAssetsAsSpam } = useSpamAsset();

  const draftState = useSnapshotDraft(loaded);
  const { commit, draft, isDirty } = draftState;

  const netWorth = computed<BigNumber>(() => {
    const current = get(draft);
    return current ? getTotalValue(current.locationDataSnapshot) : Zero;
  });

  async function load(): Promise<void> {
    if (!get(loaded))
      set(loading, true);
    set(loadError, undefined);
    try {
      set(loaded, await fetchSnapshot(toValue(timestamp)));
    }
    catch (error: unknown) {
      set(loadError, getErrorMessage(error));
    }
    finally {
      set(loading, false);
    }
  }

  watch(() => toValue(timestamp), load, { immediate: true });

  async function save(): Promise<void> {
    set(saving, true);
    set(modelActionError, undefined);
    try {
      const result = await commit(
        async snapshot => persist(toValue(timestamp), snapshot),
        async assets => markAssetsAsSpam(assets, { silent: true }),
      );
      if (!result.saved) {
        set(modelActionError, t('dashboard.snapshot.detail.save.failure'));
        return;
      }
      if (result.spamError === undefined)
        set(modelSaveSuccess, true);
      else
        set(modelActionError, t('dashboard.snapshot.detail.save.spam_failure', { message: result.spamError }));
      await refreshNetValue();
    }
    catch (error: unknown) {
      set(modelActionError, getErrorMessage(error));
    }
    finally {
      set(saving, false);
    }
  }

  async function performDelete(): Promise<void> {
    set(modelActionError, undefined);
    try {
      const success = await remove(toValue(timestamp));
      if (success) {
        await refreshNetValue();
        await router.push('/statistics/snapshots');
        return;
      }
      set(modelActionError, t('dashboard.snapshot.delete.message.failure'));
    }
    catch (error: unknown) {
      set(modelActionError, getErrorMessage(error));
    }
  }

  watch(isDirty, (dirty) => {
    if (dirty)
      set(modelSaveSuccess, false);
  });

  /** Lets the user leave an edited snapshot, by prev/next or any other navigation, only once they agree. */
  async function confirmLeave(): Promise<boolean> {
    if (!get(isDirty))
      return true;

    return await ask({
      message: t('dashboard.snapshot.detail.leave.message'),
      title: t('dashboard.snapshot.detail.leave.title'),
    }) === 'confirm';
  }

  onBeforeRouteLeave(confirmLeave);

  /**
   * Raises the browser's own leave prompt for an unsaved snapshot.
   *
   * @remarks
   * Covers what the route guard above cannot see: a refresh, a tab close and an Electron window close
   * all bypass in-app navigation. Legacy Chromium needs `returnValue` set for the prompt to appear.
   *
   * @param event - the pending unload, cancelled to raise the prompt
   */
  function warnBeforeUnload(event: BeforeUnloadEvent): void {
    if (!get(isDirty))
      return;

    event.preventDefault();
    event.returnValue = '';
  }

  useEventListener(window, 'beforeunload', warnBeforeUnload);

  return {
    ...draftState,
    loadError: readonly(loadError),
    loading: readonly(loading),
    modelActionError,
    modelSaveSuccess,
    netWorth,
    performDelete,
    save,
    saving: readonly(saving),
  };
}
