import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AssetUpdateConflictResult, AssetVersionUpdate, ConflictResolution } from '@/modules/assets/types';
import { useAssets } from '@/modules/assets/use-assets';
import { useRestartingStatus } from '@/modules/auth/use-restarting-status';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { SKIP_ASSET_UPDATE_KEY, SKIPPED_ASSET_VERSION_KEY } from '@/modules/shell/app/asset-update-keys';
import { useBackendReload } from '@/modules/shell/app/use-backend-reload';

interface UseAssetUpdateOptions {
  /**
   * Runs the update as the only thing on screen, before login.
   *
   * @remarks
   * Changes three behaviours rather than only the layout: the check runs on mount, a skipped
   * version short-circuits it, and "nothing to update" reports through `onSkip` instead of a
   * success message the user has nowhere to read.
   */
  headless: MaybeRefOrGetter<boolean>;
  /** Called whenever this surface is finished and the app should move on. */
  onSkip: () => void;
}

interface UseAssetUpdateReturn {
  /** True while the update is being written. */
  applying: Readonly<Ref<boolean>>;
  /** True while the remote version is being read. */
  checking: Readonly<Ref<boolean>>;
  /** Conflicts the last apply reported, for the resolution dialog. */
  conflicts: Readonly<Ref<AssetUpdateConflictResult[]>>;
  /** Asks the backend whether an update exists, and opens the prompt if one does. */
  check: () => Promise<void>;
  /** True once a headless update finished and wants its own inline confirmation. */
  inlineConfirm: Readonly<Ref<boolean>>;
  /** The versions in play; written back by the message component when the user retargets. */
  modelChanges: Ref<AssetVersionUpdate>;
  /** Whether the conflict-resolution dialog is open. */
  modelShowConflictDialog: Ref<boolean>;
  /** Whether the update prompt is open. */
  showUpdateDialog: Readonly<Ref<boolean>>;
  /**
   * Dismisses the prompt and hands back to the app.
   *
   * @param skipUpdate - also remembers this remote version, so it is not offered again
   */
  skip: (skipUpdate: boolean) => void;
  /** The remote version the user previously skipped, or 0 when none. */
  skipped: Readonly<Ref<number>>;
  /** What the surface is busy doing, or null when idle. */
  status: ComputedRef<'checking' | 'applying' | null>;
  /** Restarts the backend so the new assets are served; a no-op while one is already restarting. */
  updateComplete: () => Promise<void>;
  /** Writes the update, resolving conflicts with `resolution` when the user supplied one. */
  updateAssets: (resolution?: ConflictResolution) => Promise<void>;
}

/**
 * Drives the asset-database update: the version check, the prompt, conflict resolution, and the
 * backend restart that serves the result.
 *
 * @remarks
 * This overwrites the local asset database, so nothing is written until the user accepts the
 * prompt. A successful apply clears the skipped version, on the grounds that the thing the user
 * was avoiding has now happened.
 *
 * @returns the surface's bindings; only {@link UseAssetUpdateReturn.updateAssets} writes anything
 */
export function useAssetUpdate(options: UseAssetUpdateOptions): UseAssetUpdateReturn {
  const { headless, onSkip } = options;

  const checking = shallowRef<boolean>(false);
  const applying = shallowRef<boolean>(false);
  const inlineConfirm = shallowRef<boolean>(false);
  const showUpdateDialog = shallowRef<boolean>(false);
  const modelShowConflictDialog = shallowRef<boolean>(false);
  const conflicts = ref<AssetUpdateConflictResult[]>([]);
  const modelChanges = ref<AssetVersionUpdate>({
    changes: 0,
    local: 0,
    remote: 0,
    upToVersion: 0,
  });

  const skipped = useLocalStorage(SKIPPED_ASSET_VERSION_KEY, 0);

  const { t } = useI18n({ useScope: 'global' });
  const { applyUpdates, checkForUpdate } = useAssets();
  const { reload } = useBackendReload();
  const { setMessage } = useMessageStore();
  const { restarting } = useRestartingStatus();
  const { show } = useConfirmStore();

  const status = computed<'checking' | 'applying' | null>(() => {
    if (get(checking))
      return 'checking';

    if (get(applying))
      return 'applying';

    return null;
  });

  async function check(): Promise<void> {
    set(checking, true);
    const checkResult = await checkForUpdate();
    set(checking, false);

    const skippedVersion = get(skipped);
    const versions = checkResult.versions;

    if (toValue(headless) && skippedVersion && skippedVersion === versions?.remote) {
      onSkip();
      return;
    }

    set(showUpdateDialog, checkResult.updateAvailable);

    if (!checkResult.updateAvailable) {
      if (toValue(headless)) {
        onSkip();
      }
      else {
        setMessage({
          description: t('asset_update.up_to_date'),
          success: true,
        });
      }
    }

    if (versions) {
      set(modelChanges, {
        changes: versions.newChanges,
        local: versions.local,
        remote: versions.remote,
        upToVersion: versions.remote,
      });
    }
  }

  function skip(skipUpdate: boolean): void {
    set(showUpdateDialog, false);
    set(modelShowConflictDialog, false);
    if (skipUpdate)
      set(skipped, get(modelChanges).remote);

    onSkip();
  }

  async function updateComplete(): Promise<void> {
    if (get(restarting))
      return;

    set(restarting, true);
    try {
      await reload();
    }
    finally {
      set(restarting, false);
    }
  }

  function showDoneConfirmation(): void {
    if (toValue(headless)) {
      set(inlineConfirm, true);
      return;
    }

    show(
      {
        message: t('asset_update.success.description', {
          remoteVersion: get(modelChanges).upToVersion,
        }),
        primaryAction: t('common.actions.ok'),
        singleAction: true,
        title: t('asset_update.success.title'),
        type: 'success',
      },
      updateComplete,
    );
  }

  async function updateAssets(resolution?: ConflictResolution): Promise<void> {
    set(showUpdateDialog, false);
    set(modelShowConflictDialog, false);
    const version = get(modelChanges).upToVersion;
    set(applying, true);
    const updateResult = await applyUpdates({ resolution, version });
    set(applying, false);

    if (updateResult.done) {
      set(skipped, 0);
      showDoneConfirmation();
    }
    else if (updateResult.conflicts) {
      set(conflicts, updateResult.conflicts);
      set(modelShowConflictDialog, true);
    }
  }

  onMounted(async () => {
    if (sessionStorage.getItem(SKIP_ASSET_UPDATE_KEY)) {
      onSkip();
      return;
    }

    if (toValue(headless))
      await check();
  });

  return {
    applying: readonly(applying),
    check,
    checking: readonly(checking),
    conflicts: shallowReadonly(conflicts),
    inlineConfirm: readonly(inlineConfirm),
    modelChanges,
    modelShowConflictDialog,
    showUpdateDialog: readonly(showUpdateDialog),
    skip,
    skipped: readonly(skipped),
    status,
    updateAssets,
    updateComplete,
  };
}
