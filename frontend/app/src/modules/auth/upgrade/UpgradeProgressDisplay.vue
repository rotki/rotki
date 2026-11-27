<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { startPromise } from '@shared/utils';
import { useIntervalFn, useTimestamp } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, onMounted, ref, watch } from 'vue';
import { useNewlyDetectedTokens } from '@/modules/assets/detection/use-newly-detected-tokens';
import DbActivityProgress from '@/modules/auth/upgrade/DbActivityProgress.vue';
import {
  computeUpgradeProgress,
  profileDirectory,
  UpgradeKind,
  UpgradeOutcome,
  type UpgradeRunInput,
  type UpgradeRunProgress,
  type UpgradeRunView,
  versionDurations,
} from '@/modules/auth/upgrade/upgrade-progress';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { loadUserOptions } from '@/modules/shell/app/backend-options';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const { completed = false } = defineProps<{
  /** The unlock got past the upgrade and the session is loading, so the run is finished. */
  completed?: boolean;
}>();

const emit = defineEmits<{
  back: [];
}>();

interface UpgradeView {
  kind: UpgradeKind;
  input: UpgradeRunInput;
  fromVersion: number;
  description: string;
  times: Readonly<Record<number, number>>;
}

const authStore = useSessionAuthStore();
const {
  dataMigrationStatus,
  dataMigrationVersionTimes,
  dbUpgradeStatus,
  dbUpgradeVersionTimes,
  unlockingProfile,
  upgradeFailure,
  upgradeStartedAt,
} = storeToRefs(authStore);
const { dataDirectory } = storeToRefs(useMainStore());
const interop = useInterop();

const outcome = computed<UpgradeOutcome>(() => {
  if (get(upgradeFailure) !== null)
    return UpgradeOutcome.FAILED;
  return completed ? UpgradeOutcome.DONE : UpgradeOutcome.RUNNING;
});

/**
 * The run on screen. Data migrations follow the DB upgrade in the same unlock and take over while
 * they run; a finished unlock that upgraded the DB reports the upgrade, which is the news.
 */
const view = computed<UpgradeView | undefined>(() => {
  const upgrade = get(dbUpgradeStatus);
  const migration = get(dataMigrationStatus);

  if (migration && !(upgrade && get(outcome) === UpgradeOutcome.DONE)) {
    const { currentStep, description, totalSteps, version } = migration.currentMigration;
    return {
      description: description ?? '',
      fromVersion: migration.startVersion,
      input: { currentStep, currentVersion: version, startVersion: migration.startVersion, targetVersion: migration.targetVersion, totalSteps },
      kind: UpgradeKind.DATA_MIGRATION,
      times: get(dataMigrationVersionTimes),
    };
  }

  if (upgrade) {
    const { currentStep, description, toVersion, totalSteps } = upgrade.currentUpgrade;
    return {
      description: description ?? '',
      fromVersion: upgrade.startVersion - 1,
      input: { currentStep, currentVersion: toVersion, startVersion: upgrade.startVersion, targetVersion: upgrade.targetVersion, totalSteps },
      kind: UpgradeKind.DB_UPGRADE,
      times: get(dbUpgradeVersionTimes),
    };
  }
  return undefined;
});

const progress = computed<UpgradeRunProgress | undefined>(() => {
  const current = get(view);
  return current ? computeUpgradeProgress(current.input, get(outcome)) : undefined;
});

const now = useTimestamp({ scheduler: tick => useIntervalFn(tick, 1000) });
/** When the run settled, which freezes the elapsed time and the last version's duration. */
const settledAt = ref<number>();

watch(outcome, (current) => {
  set(settledAt, current === UpgradeOutcome.RUNNING ? undefined : Date.now());
}, { immediate: true });

const clock = computed<number>(() => get(settledAt) ?? get(now));

const elapsed = computed<number | undefined>(() => {
  const startedAt = get(upgradeStartedAt);
  return startedAt === null ? undefined : Math.max(0, get(clock) - startedAt);
});

const durations = computed<Record<number, number>>(() => {
  const current = get(view);
  const run = get(progress);
  if (!current || !run)
    return {};
  return versionDurations(run.versions, current.times, get(clock));
});

const run = computed<UpgradeRunView | undefined>(() => {
  const current = get(view);
  const runProgress = get(progress);
  if (!current || !runProgress)
    return undefined;
  return {
    description: current.description,
    durations: get(durations),
    elapsed: get(elapsed),
    fromVersion: current.fromVersion,
    kind: current.kind,
    outcome: get(outcome),
    progress: runProgress,
    toVersion: current.input.targetVersion,
  };
});

/** Only the desktop app on its own backend can open folders, and only there are the paths local. */
const canOpenPaths = interop.appSession;

const backupDirectory = computed<string | undefined>(() => profileDirectory(get(dataDirectory), get(unlockingProfile)));

async function openLogs(): Promise<void> {
  const { logDirectory: configured } = await interop.config(false);
  const logDirectory = configured ?? loadUserOptions().logDirectory ?? (await interop.config(true)).logDirectory;
  if (logDirectory)
    await interop.openPath(logDirectory);
}

async function openBackups(): Promise<void> {
  const directory = get(backupDirectory);
  if (directory)
    await interop.openPath(directory);
}

const { clearInternalTokens } = useNewlyDetectedTokens();

onMounted(() => {
  if (get(dbUpgradeStatus))
    clearInternalTokens();
});
</script>

<template>
  <DbActivityProgress
    v-if="run"
    :run="run"
    :profile="unlockingProfile"
    :error="upgradeFailure ?? undefined"
    :backup-directory="backupDirectory"
    :can-open-paths="canOpenPaths"
    @back="emit('back')"
    @open-logs="startPromise(openLogs())"
    @open-backups="startPromise(openBackups())"
    @report="startPromise(interop.openUrl(externalLinks.githubNewBugReport))"
  />
</template>
