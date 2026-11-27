<script setup lang="ts">
import type { AssetUpdateConflictResult, AssetVersionUpdate, ConflictResolution } from '@/modules/assets/types';
import { externalLinks } from '@shared/external-links';
import { startPromise } from '@shared/utils';
import { useLocalStorage } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import AssetConflictStage from '@/modules/auth/unlock-flow/AssetConflictStage.vue';
import AssetUpdateProgress from '@/modules/auth/unlock-flow/AssetUpdateProgress.vue';
import AssetUpdatePrompt from '@/modules/auth/unlock-flow/AssetUpdatePrompt.vue';
import { isUpgradeCompleted, showsUpgrade } from '@/modules/auth/unlock-flow/upgrade-stage';
import { UnlockErrorKind, UnlockPhase, type UnlockState } from '@/modules/auth/unlock-flow/use-unlock-flow';
import UpgradeProgressDisplay from '@/modules/auth/upgrade/UpgradeProgressDisplay.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { AUTO_APPLY_ASSET_UPDATES_KEY, SKIPPED_ASSET_VERSION_KEY } from '@/modules/shell/app/asset-update-keys';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const { state, updateAccepted = false } = defineProps<{
  state: UnlockState;
  /** Whether the user accepted an asset update in this unlock, which keeps its progress on screen to the end. */
  updateAccepted?: boolean;
}>();

const emit = defineEmits<{
  'confirm': [upToVersion: number];
  'resolve': [resolution: ConflictResolution];
  'skip': [];
  'leave-upgrade': [];
  'leave-update': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { upgradeFailure, upgradeVisible } = storeToRefs(useSessionAuthStore());
const interop = useInterop();

const skipped = useLocalStorage<number>(SKIPPED_ASSET_VERSION_KEY, 0);
const autoApply = useLocalStorage<boolean>(AUTO_APPLY_ASSET_UPDATES_KEY, false);

const promptedVersions = ref<AssetVersionUpdate>({ changes: 0, local: 0, remote: 0, upToVersion: 0 });

const phase = computed<string>(() => state.kind);

const upgradeCompleted = computed<boolean>(() => isUpgradeCompleted(get(phase)));

const showUpgrade = computed<boolean>(() => showsUpgrade(get(phase), get(upgradeVisible), get(upgradeFailure) !== null));

const conflicts = computed<AssetUpdateConflictResult[]>(() => (state.kind === UnlockPhase.conflicts ? state.conflicts : []));

const errorKind = computed<string | undefined>(() => (state.kind === UnlockPhase.error ? state.error.kind : undefined));

/** What the flow said when it stopped, worded for the asset update progress. */
const errorMessage = computed<string | undefined>(() => {
  if (state.kind !== UnlockPhase.error)
    return undefined;
  const { error } = state;
  if (error.kind === UnlockErrorKind.restartFailed)
    return t('unlock_flow.errors.restart_failed');
  if (error.kind === UnlockErrorKind.updateFailed || error.kind === UnlockErrorKind.unknown)
    return error.message;
  return undefined;
});

function confirm({ always, upToVersion }: { upToVersion: number; always: boolean }): void {
  if (always)
    set(autoApply, true);
  set(promptedVersions, { ...get(promptedVersions), upToVersion });
  emit('confirm', upToVersion);
}

function skip(remember: boolean): void {
  if (remember)
    set(skipped, get(promptedVersions).remote);
  emit('skip');
}

/** Whether this run applies the update without having asked, which the progress screen says. */
const automatic = ref<boolean>(false);

watch(() => state, (current) => {
  if (current.kind === UnlockPhase.updatePrompt || current.kind === UnlockPhase.applyingUpdate)
    set(promptedVersions, { ...current.changes });
  if (current.kind === UnlockPhase.applyingUpdate)
    set(automatic, current.automatic);
}, { immediate: true });
</script>

<template>
  <AssetUpdatePrompt
    v-if="phase === UnlockPhase.updatePrompt"
    :versions="promptedVersions"
    @confirm="confirm($event)"
    @skip="skip($event)"
  />
  <AssetConflictStage
    v-else-if="phase === UnlockPhase.conflicts"
    :conflicts="conflicts"
    :version="promptedVersions.upToVersion"
    @resolve="emit('resolve', $event)"
    @skip="emit('skip')"
  />
  <UpgradeProgressDisplay
    v-else-if="showUpgrade"
    :completed="upgradeCompleted"
    @back="emit('leave-upgrade')"
  />
  <AssetUpdateProgress
    v-else-if="updateAccepted"
    :phase="phase"
    :from="promptedVersions.local"
    :to="promptedVersions.upToVersion"
    :automatic="automatic"
    :error="errorMessage"
    :error-kind="errorKind"
    @back="emit('leave-update')"
    @report="startPromise(interop.openUrl(externalLinks.githubNewBugReport))"
  />
</template>
