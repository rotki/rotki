<script setup lang="ts">
import { RuiAlert, RuiButton, RuiCard, RuiIcon, RuiProgress } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  parseUpgradeFailure,
  UpgradeKind,
  UpgradeOutcome,
  UpgradeRowStatus,
  type UpgradeRunProgress,
  type UpgradeRunView,
  type UpgradeVersionRow,
  type UpgradeVersionWindow,
  windowVersions,
} from '@/modules/auth/upgrade/upgrade-progress';
import { useCopy } from '@/modules/core/common/use-clipboard';
import { formatElapsed } from '@/modules/task-center/core/elapsed';

const {
  backupDirectory,
  canOpenPaths = false,
  error,
  profile,
  run,
} = defineProps<{
  run: UpgradeRunView;
  profile: string;
  error?: string;
  /** Where the backend keeps its pre-upgrade copies of this profile's database. */
  backupDirectory?: string;
  /** Whether folders can be opened from here, which only the desktop app can do. */
  canOpenPaths?: boolean;
}>();

const emit = defineEmits<{
  'back': [];
  'open-backups': [];
  'open-logs': [];
  'report': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const progress = computed<UpgradeRunProgress>(() => run.progress);
const outcome = computed<UpgradeOutcome>(() => run.outcome);
const isMigration = computed<boolean>(() => run.kind === UpgradeKind.DATA_MIGRATION);
const running = computed<boolean>(() => run.outcome === UpgradeOutcome.RUNNING);
const done = computed<boolean>(() => run.outcome === UpgradeOutcome.DONE);
const failed = computed<boolean>(() => run.outcome === UpgradeOutcome.FAILED);

const title = computed<string>(() => {
  if (get(failed))
    return t('login.db_upgrade.title.failed');
  if (get(isMigration))
    return get(done) ? t('login.db_upgrade.title.migrated') : t('login.db_upgrade.title.migrating');
  return get(done) ? t('login.db_upgrade.title.done', { version: run.toVersion }) : t('login.db_upgrade.title.running');
});

const range = computed<string>(() => (get(isMigration)
  ? t('login.db_upgrade.range.migration', { from: run.fromVersion, to: run.toVersion })
  : t('login.db_upgrade.range.version', { from: run.fromVersion, to: run.toVersion })));

/** "Version 2 of 3 · step 17 of 17", or the preparing line while nothing countable is known. */
const summary = computed<string>(() => {
  const { currentStep, percentage, stepsKnown, totalSteps, versionCount, versionIndex } = get(progress);
  if (percentage === undefined)
    return t('login.db_upgrade.progress.preparing');
  const position = get(isMigration)
    ? t('login.db_upgrade.progress.migration', { count: versionCount, index: versionIndex })
    : t('login.db_upgrade.progress.version', { count: versionCount, index: versionIndex });
  if (!stepsKnown || get(done))
    return position;
  return `${position} · ${t('login.db_upgrade.progress.step', { current: currentStep, total: totalSteps })}`;
});

const barColor = computed<'primary' | 'success' | 'error'>(() => {
  if (get(failed))
    return 'error';
  return get(done) ? 'success' : 'primary';
});

const indeterminate = computed<boolean>(() => get(progress).percentage === undefined);

const elapsedText = computed<string | undefined>(() => (run.elapsed === undefined ? undefined : formatElapsed(run.elapsed)));

/** The line under the summary: the step the backend is on, or how long a finished run took. */
const detail = computed<string>(() => {
  if (get(done))
    return get(elapsedText) ? t('login.db_upgrade.done.took', { time: get(elapsedText) }) : '';
  return get(running) ? run.description : '';
});

const versionWindow = computed<UpgradeVersionWindow>(() => windowVersions(get(progress).versions));

/** Set only when the backend reported the upgrade itself failed, which is when it restored the backup. */
const restored = computed<{ restoredVersion: number; failedVersion: number } | undefined>(() => (error && !get(isMigration) ? parseUpgradeFailure(error) : undefined));

function rowLabel(row: UpgradeVersionRow): string {
  return get(isMigration)
    ? t('login.db_upgrade.rows.migration', { version: row.version })
    : t('login.db_upgrade.rows.version', { version: row.version });
}

/** A done row shows how long it took, the current row its steps while it runs. */
function rowMeta(row: UpgradeVersionRow): string | undefined {
  const { currentStep, stepsKnown, totalSteps } = get(progress);
  if (row.status === UpgradeRowStatus.CURRENT && get(running) && stepsKnown)
    return `${currentStep}/${totalSteps}`;
  if (row.status === UpgradeRowStatus.PENDING)
    return undefined;
  const duration = run.durations[row.version];
  return duration === undefined ? undefined : formatElapsed(duration);
}

/** What Copy error puts on the clipboard: the error, the run it broke, and where the backups are. */
const errorReport = computed<string>(() => [error, get(range), backupDirectory].filter(Boolean).join('\n'));
const { copied, copy } = useCopy(errorReport);

function copyError(): void {
  startPromise(copy());
}
</script>

<template>
  <section
    class="w-full max-w-120 mx-auto flex flex-col gap-6"
    :data-outcome="outcome"
    data-testid="db-upgrade"
  >
    <header>
      <h1
        class="text-h4 mb-2"
        data-testid="db-upgrade-title"
      >
        {{ title }}
      </h1>
      <p
        v-if="!profile"
        class="text-body-1 text-rui-text-secondary"
        data-testid="db-upgrade-subtitle"
      >
        {{ range }}
      </p>
      <i18n-t
        v-else
        scope="global"
        keypath="login.db_upgrade.subtitle"
        tag="p"
        class="text-body-1 text-rui-text-secondary break-words"
        data-testid="db-upgrade-subtitle"
      >
        <template #profile>
          <span class="font-medium text-rui-text">{{ profile }}</span>
        </template>
        <template #range>
          {{ range }}
        </template>
      </i18n-t>
    </header>

    <RuiCard
      variant="outlined"
      no-padding
      class="overflow-hidden"
    >
      <div class="p-4 flex flex-col gap-3">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex flex-col gap-0.5">
            <div
              class="text-body-1 font-medium"
              aria-live="polite"
              data-testid="db-upgrade-summary"
            >
              <template v-if="done">
                {{ t('login.db_upgrade.done.opening') }}
              </template>
              <template v-else>
                {{ summary }}
              </template>
            </div>
            <!-- Always one line tall, so a step without a name or with a long one moves nothing below it. -->
            <div
              class="text-body-2 text-rui-text-secondary h-5 truncate"
              :title="detail"
              data-testid="db-upgrade-description"
            >
              {{ detail }}
            </div>
          </div>
          <div
            v-if="elapsedText && !done"
            class="shrink-0 flex items-center gap-1 text-body-2 text-rui-text-secondary tabular-nums"
            :title="t('login.db_upgrade.elapsed')"
            data-testid="db-upgrade-elapsed"
          >
            <RuiIcon
              name="lu-clock"
              size="14"
            />
            <span class="sr-only">{{ t('login.db_upgrade.elapsed') }}</span>
            <span>{{ elapsedText }}</span>
          </div>
        </div>

        <RuiProgress
          :color="barColor"
          :variant="indeterminate ? 'indeterminate' : 'determinate'"
          :value="progress.percentage ?? 0"
          :aria-label="summary"
          data-testid="db-upgrade-bar"
        />
      </div>

      <div class="border-t border-default px-4 py-3">
        <ul
          class="flex flex-col ml-2 pl-3 border-l border-default"
          :aria-label="isMigration ? t('login.db_upgrade.rows.migration_label') : t('login.db_upgrade.rows.label')"
          data-testid="db-upgrade-versions"
        >
          <li
            v-if="versionWindow.hiddenDone > 0"
            class="flex items-center gap-2.5 py-1 text-body-2 text-rui-text-secondary"
            data-testid="db-upgrade-hidden-done"
          >
            <RuiIcon
              name="lu-check"
              size="16"
              class="text-rui-success shrink-0"
            />
            {{ t('login.db_upgrade.rows.earlier', { count: versionWindow.hiddenDone }, versionWindow.hiddenDone) }}
          </li>
          <li
            v-for="row in versionWindow.rows"
            :key="row.version"
            class="flex items-center gap-2.5 py-1 text-body-2"
            :data-status="row.status"
            data-testid="db-upgrade-version"
          >
            <span class="size-4 shrink-0 flex items-center justify-center">
              <RuiIcon
                v-if="row.status === UpgradeRowStatus.DONE"
                name="lu-check"
                size="16"
                class="text-rui-success"
              />
              <RuiIcon
                v-else-if="row.status === UpgradeRowStatus.CURRENT && failed"
                name="lu-circle-x"
                size="16"
                class="text-rui-error"
              />
              <RuiProgress
                v-else-if="row.status === UpgradeRowStatus.CURRENT"
                circular
                color="primary"
                size="16"
                thickness="2"
                :variant="progress.stepPercentage === undefined ? 'indeterminate' : 'determinate'"
                :value="progress.stepPercentage ?? 0"
              />
              <span
                v-else
                class="size-3 rounded-full border-2 border-rui-grey-400 dark:border-rui-grey-600"
              />
            </span>
            <span
              class="flex-1 min-w-0 truncate"
              :class="{
                'font-medium': row.status === UpgradeRowStatus.CURRENT,
                'text-rui-text-secondary': row.status !== UpgradeRowStatus.CURRENT,
                'text-rui-error': row.status === UpgradeRowStatus.CURRENT && failed,
              }"
            >
              {{ rowLabel(row) }}
            </span>
            <span
              v-if="rowMeta(row)"
              class="shrink-0 text-caption text-rui-text-secondary tabular-nums"
            >
              {{ rowMeta(row) }}
            </span>
          </li>
          <li
            v-if="versionWindow.hiddenPending > 0"
            class="py-1 pl-6.5 text-body-2 text-rui-text-secondary"
            data-testid="db-upgrade-hidden-pending"
          >
            {{ t('login.db_upgrade.rows.more', { count: versionWindow.hiddenPending }, versionWindow.hiddenPending) }}
          </li>
        </ul>
      </div>
    </RuiCard>

    <div
      v-if="running"
      class="flex gap-3 text-body-2 text-rui-text-secondary"
      data-testid="db-upgrade-reassurance"
    >
      <RuiIcon
        name="lu-shield-check"
        size="20"
        class="shrink-0 mt-0.5 text-rui-primary"
      />
      <div class="flex flex-col gap-2">
        <p v-if="isMigration">
          {{ t('login.db_upgrade.reassurance.migration') }}
        </p>
        <template v-else>
          <p>{{ t('login.db_upgrade.reassurance.backup') }}</p>
          <p>{{ t('login.db_upgrade.reassurance.keep_open') }}</p>
          <p>{{ t('login.db_upgrade.reassurance.slow') }}</p>
        </template>
      </div>
    </div>

    <div
      v-else-if="failed"
      class="flex flex-col gap-4"
      data-testid="db-upgrade-failure"
    >
      <RuiAlert
        v-if="error"
        type="error"
      >
        <span
          class="break-words"
          data-testid="db-upgrade-error"
        >
          {{ error }}
        </span>
      </RuiAlert>

      <div class="flex flex-col gap-2 text-body-2 text-rui-text-secondary">
        <p
          v-if="restored"
          data-testid="db-upgrade-restored"
        >
          {{ t('login.db_upgrade.failed.restored', { previous: restored.restoredVersion, version: restored.failedVersion }) }}
        </p>
        <template v-if="!isMigration && backupDirectory">
          <p>{{ restored ? t('login.db_upgrade.failed.backups') : t('login.db_upgrade.failed.backups_kept') }}</p>
          <code
            class="block rounded-md bg-rui-grey-100 dark:bg-rui-grey-800 px-3 py-2 text-caption text-rui-text break-all"
            data-testid="db-upgrade-backup-path"
          >
            {{ backupDirectory }}
          </code>
        </template>
        <p>{{ t('login.db_upgrade.failed.next_steps') }}</p>
        <p v-if="!canOpenPaths">
          {{ t('login.db_upgrade.failed.logs_web') }}
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <RuiButton
          color="primary"
          data-testid="db-upgrade-back"
          @click="emit('back')"
        >
          {{ t('login.db_upgrade.failed.actions.back') }}
        </RuiButton>
        <RuiButton
          v-if="error"
          variant="outlined"
          color="primary"
          data-testid="db-upgrade-copy"
          @click="copyError()"
        >
          <template #prepend>
            <RuiIcon
              v-if="copied"
              name="lu-check"
              size="16"
            />
            <RuiIcon
              v-else
              name="lu-copy"
              size="16"
            />
          </template>
          {{ copied ? t('login.db_upgrade.failed.actions.copied') : t('login.db_upgrade.failed.actions.copy') }}
        </RuiButton>
        <RuiButton
          v-if="canOpenPaths"
          variant="outlined"
          color="primary"
          data-testid="db-upgrade-open-logs"
          @click="emit('open-logs')"
        >
          {{ t('login.db_upgrade.failed.actions.open_logs') }}
        </RuiButton>
        <RuiButton
          v-if="canOpenPaths && backupDirectory && !isMigration"
          variant="outlined"
          color="primary"
          data-testid="db-upgrade-open-backups"
          @click="emit('open-backups')"
        >
          {{ t('login.db_upgrade.failed.actions.open_folder') }}
        </RuiButton>
        <RuiButton
          variant="text"
          color="primary"
          data-testid="db-upgrade-report"
          @click="emit('report')"
        >
          {{ t('login.db_upgrade.failed.actions.report') }}
        </RuiButton>
      </div>
    </div>
  </section>
</template>
