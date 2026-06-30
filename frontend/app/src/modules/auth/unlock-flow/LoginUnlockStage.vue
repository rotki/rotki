<script setup lang="ts">
import type { AssetUpdateConflictResult, AssetVersionUpdate, ConflictResolution } from '@/modules/assets/types';
import { UnlockPhase, type UnlockState } from '@/modules/auth/unlock-flow/use-unlock-flow';
import UpgradeProgressDisplay from '@/modules/auth/upgrade/UpgradeProgressDisplay.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import AssetConflictDialog from '@/modules/shell/app/AssetConflictDialog.vue';
import AssetUpdateMessage from '@/modules/shell/app/AssetUpdateMessage.vue';
import AssetUpdateStatus from '@/modules/shell/app/AssetUpdateStatus.vue';

const { state } = defineProps<{
  state: UnlockState;
}>();

const emit = defineEmits<{
  confirm: [upToVersion: number];
  resolve: [resolution: ConflictResolution];
  skip: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { upgradeVisible } = storeToRefs(useSessionAuthStore());

// A specific remote version the user permanently skipped (shared with the check step).
const skipped = useLocalStorage<number>('rotki_skip_asset_db_version', 0);

// Editable copy the asset-update prompt v-models; seeded when the flow suspends on the prompt.
const versions = ref<AssetVersionUpdate>({ changes: 0, local: 0, remote: 0, upToVersion: 0 });

const phase = computed<string>(() => state.kind);

const conflicts = computed<AssetUpdateConflictResult[]>(() => (state.kind === UnlockPhase.conflicts ? state.conflicts : []));

// In-flight phases with no dedicated UI fall back to the indeterminate spinner.
const busy = computed<boolean>(() => {
  const kind = phase.value;
  return kind === UnlockPhase.authenticating
    || kind === UnlockPhase.connecting
    || kind === UnlockPhase.restarting
    || kind === UnlockPhase.unlocking
    || kind === UnlockPhase.loadingSession
    || kind === UnlockPhase.ready;
});

// A label for the busy spinner where a phase warrants one (restart / unlock).
const busyMessage = computed<string>(() => {
  if (phase.value === UnlockPhase.restarting)
    return t('unlock_flow.status.restarting');
  if (phase.value === UnlockPhase.unlocking)
    return t('unlock_flow.status.unlocking');
  return '';
});

function dismiss(skip: boolean): void {
  if (skip)
    set(skipped, get(versions).remote);
  emit('skip');
}

watch(() => state, (current) => {
  if (current.kind === UnlockPhase.updatePrompt)
    set(versions, { ...current.changes });
}, { immediate: true });
</script>

<template>
  <AssetUpdateMessage
    v-if="phase === UnlockPhase.updatePrompt"
    v-model:versions="versions"
    class="max-w-[32rem] mx-auto"
    headless
    @confirm="emit('confirm', versions.upToVersion)"
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
    class="max-w-[32rem] mx-auto"
    status="applying"
    :remote-version="versions.upToVersion"
  />
  <AssetUpdateStatus
    v-else-if="phase === UnlockPhase.checkingUpdate"
    class="max-w-[32rem] mx-auto"
    status="checking"
    :remote-version="0"
  />
  <UpgradeProgressDisplay v-else-if="phase === UnlockPhase.unlocking && upgradeVisible" />
  <div
    v-else-if="busy"
    class="flex flex-col gap-4 justify-center items-center py-12"
  >
    <RuiProgress
      color="primary"
      variant="indeterminate"
      circular
      size="48"
    />
    <p
      v-if="busyMessage"
      class="mb-0 text-rui-text-secondary"
    >
      {{ busyMessage }}
    </p>
  </div>
</template>
