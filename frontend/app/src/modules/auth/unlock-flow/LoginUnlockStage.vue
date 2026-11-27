<script setup lang="ts">
import type { AssetUpdateConflictResult, AssetVersionUpdate, ConflictResolution } from '@/modules/assets/types';
import { RuiProgress } from '@rotki/ui-library';
import { useLocalStorage } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { UnlockPhase, type UnlockState } from '@/modules/auth/unlock-flow/use-unlock-flow';
import UpgradeProgressDisplay from '@/modules/auth/upgrade/UpgradeProgressDisplay.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { SKIPPED_ASSET_VERSION_KEY } from '@/modules/shell/app/asset-update-keys';
import AssetConflictDialog from '@/modules/shell/app/AssetConflictDialog.vue';
import AssetUpdateMessage from '@/modules/shell/app/AssetUpdateMessage.vue';
import AssetUpdateStatus from '@/modules/shell/app/AssetUpdateStatus.vue';

const { state } = defineProps<{
  state: UnlockState;
}>();

const emit = defineEmits<{
  'confirm': [upToVersion: number];
  'resolve': [resolution: ConflictResolution];
  'skip': [];
  'leave-upgrade': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { upgradeFailure, upgradeVisible } = storeToRefs(useSessionAuthStore());

const skipped = useLocalStorage<number>(SKIPPED_ASSET_VERSION_KEY, 0);

const promptedVersions = ref<AssetVersionUpdate>({ changes: 0, local: 0, remote: 0, upToVersion: 0 });

const phase = computed<string>(() => state.kind);

/** The unlock got past the upgrade, so the upgrade screen reports it finished. */
const upgradeCompleted = computed<boolean>(() => {
  const kind = get(phase);
  return kind === UnlockPhase.loadingSession || kind === UnlockPhase.ready;
});

/**
 * Whether the DB upgrade screen is up: while the upgrade runs, through the session load that
 * follows it as the "upgraded" handoff, and after a failure it caused.
 */
const showUpgrade = computed<boolean>(() => {
  if (!get(upgradeVisible))
    return false;
  const kind = get(phase);
  if (kind === UnlockPhase.error)
    return get(upgradeFailure) !== null;
  return kind === UnlockPhase.unlocking || get(upgradeCompleted);
});

const conflicts = computed<AssetUpdateConflictResult[]>(() => (state.kind === UnlockPhase.conflicts ? state.conflicts : []));

/** In-flight phases with no dedicated UI of their own, which fall back to the indeterminate spinner. */
const busy = computed<boolean>(() => {
  const kind = phase.value;
  return kind === UnlockPhase.authenticating
    || kind === UnlockPhase.connecting
    || kind === UnlockPhase.restarting
    || kind === UnlockPhase.unlocking
    || kind === UnlockPhase.loadingSession
    || kind === UnlockPhase.ready;
});

const busyMessage = computed<string>(() => {
  if (phase.value === UnlockPhase.restarting)
    return t('unlock_flow.status.restarting');
  if (phase.value === UnlockPhase.unlocking)
    return t('unlock_flow.status.unlocking');
  return '';
});

function dismiss(skip: boolean): void {
  if (skip)
    set(skipped, get(promptedVersions).remote);
  emit('skip');
}

watch(() => state, (current) => {
  if (current.kind === UnlockPhase.updatePrompt)
    set(promptedVersions, { ...current.changes });
}, { immediate: true });
</script>

<template>
  <AssetUpdateMessage
    v-if="phase === UnlockPhase.updatePrompt"
    v-model:versions="promptedVersions"
    class="max-w-110 mx-auto"
    headless
    @confirm="emit('confirm', promptedVersions.upToVersion)"
    @dismiss="dismiss($event)"
  />
  <AssetConflictDialog
    v-else-if="phase === UnlockPhase.conflicts"
    :conflicts="conflicts"
    @cancel="emit('skip')"
    @resolve="emit('resolve', $event)"
  />
  <AssetUpdateStatus
    v-else-if="phase === UnlockPhase.applyingUpdate"
    class="max-w-128 mx-auto"
    status="applying"
    :remote-version="promptedVersions.upToVersion"
  />
  <AssetUpdateStatus
    v-else-if="phase === UnlockPhase.checkingUpdate"
    class="max-w-128 mx-auto"
    status="checking"
    :remote-version="0"
  />
  <UpgradeProgressDisplay
    v-else-if="showUpgrade"
    :completed="upgradeCompleted"
    @back="emit('leave-upgrade')"
  />
  <div
    v-else-if="busy"
    class="max-w-110 mx-auto flex flex-col gap-4 justify-center items-center py-12"
  >
    <RuiProgress
      color="primary"
      variant="indeterminate"
      circular
      size="48"
    />
    <p
      v-if="busyMessage"
      class="mb-0 text-rui-text-secondary text-center"
    >
      {{ busyMessage }}
    </p>
  </div>
</template>
