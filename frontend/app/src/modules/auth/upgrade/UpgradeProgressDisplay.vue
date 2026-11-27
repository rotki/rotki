<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { startPromise } from '@shared/utils';
import { useIntervalFn, useTimestamp } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, onMounted, watch } from 'vue';
import { useNewlyDetectedTokens } from '@/modules/assets/detection/use-newly-detected-tokens';
import DbActivityProgress from '@/modules/auth/upgrade/DbActivityProgress.vue';
import {
  computeUpgradeProgress,
  profileDirectory,
  UpgradeKind,
  UpgradeOutcome,
  type UpgradeRunInput,
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

/** The parts of the run on screen that differ between a DB upgrade and a data migration. */
interface RunSource {
  kind: UpgradeKind;
  input: UpgradeRunInput;
  fromVersion: number;
  description: string | null;
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
 * Picks the run on screen. Data migrations follow the DB upgrade in the same unlock and take over
 * while they run; a finished unlock that upgraded the DB reports the upgrade, which is the news.
 */
function runSource(): RunSource | undefined {
  const upgrade = get(dbUpgradeStatus);
  const migration = get(dataMigrationStatus);

  if (migration && !(upgrade && get(outcome) === UpgradeOutcome.DONE)) {
    const { currentStep, description, totalSteps, version } = migration.currentMigration;
    const { startVersion, targetVersion } = migration;
    return {
      description,
      fromVersion: startVersion,
      input: { currentStep, currentVersion: version, startVersion, targetVersion, totalSteps },
      kind: UpgradeKind.DATA_MIGRATION,
      times: get(dataMigrationVersionTimes),
    };
  }
  if (!upgrade)
    return undefined;

  const { currentStep, description, toVersion, totalSteps } = upgrade.currentUpgrade;
  const { startVersion, targetVersion } = upgrade;
  return {
    description,
    fromVersion: startVersion - 1,
    input: { currentStep, currentVersion: toVersion, startVersion, targetVersion, totalSteps },
    kind: UpgradeKind.DB_UPGRADE,
    times: get(dbUpgradeVersionTimes),
  };
}

/** Ticks while the run is going and stops once it settles, which freezes the elapsed time. */
const { pause, resume, timestamp: now } = useTimestamp({ controls: true, scheduler: tick => useIntervalFn(tick, 1000) });

watch(outcome, (current) => {
  if (current === UpgradeOutcome.RUNNING)
    resume();
  else
    pause();
}, { immediate: true });

const run = computed<UpgradeRunView | undefined>(() => {
  const source = runSource();
  if (!source)
    return undefined;
  const result = get(outcome);
  const progress = computeUpgradeProgress(source.input, result);
  const clock = get(now);
  const startedAt = get(upgradeStartedAt);
  return {
    description: source.description ?? '',
    durations: versionDurations(progress.versions, source.times, clock),
    elapsed: startedAt === null ? undefined : Math.max(0, clock - startedAt),
    fromVersion: source.fromVersion,
    kind: source.kind,
    outcome: result,
    progress,
    toVersion: source.input.targetVersion,
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
