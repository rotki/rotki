<script setup lang="ts">
import { RuiAlert, RuiButton, RuiCard, RuiIcon, RuiProgress } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { StageStepStatus } from '@/modules/auth/stage/stage-step';
import StageLayout from '@/modules/auth/stage/StageLayout.vue';
import StageStepIcon from '@/modules/auth/stage/StageStepIcon.vue';
import {
  AssetUpdateStep,
  type AssetUpdateStepRow,
  assetUpdateSteps,
} from '@/modules/auth/unlock-flow/asset-update-progress';
import { UnlockPhase } from '@/modules/auth/unlock-flow/use-unlock-flow';
import { useCopy } from '@/modules/core/common/use-clipboard';

const { automatic = false, error, errorKind, from, phase, to } = defineProps<{
  /** Whether the update runs without having asked, as the user chose, which the screen says. */
  automatic?: boolean;
  /** The unlock flow's current phase. */
  phase: string;
  /** The asset database version before the update. */
  from: number;
  /** The version the update stops at. */
  to: number;
  /** What the flow reported when it stopped, shown in the failure state. */
  error?: string;
  /** The kind of error the flow stopped with, which says which step failed. */
  errorKind?: string;
}>();

const emit = defineEmits<{
  back: [];
  report: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const failed = computed<boolean>(() => phase === UnlockPhase.error);
const done = computed<boolean>(() => phase === UnlockPhase.ready);

const steps = computed<AssetUpdateStepRow[]>(() => assetUpdateSteps(phase, errorKind));

const title = computed<string>(() => {
  if (get(failed))
    return t('unlock_flow.asset_update.progress.title.failed');
  if (get(done))
    return t('unlock_flow.asset_update.progress.title.done', { version: to });
  return t('unlock_flow.asset_update.progress.title.running');
});

const range = computed<string>(() => t('unlock_flow.asset_update.range', { from, to }));

function stepLabel(step: AssetUpdateStep): string {
  switch (step) {
    case AssetUpdateStep.APPLY:
      return t('unlock_flow.asset_update.progress.steps.apply', { version: to });
    case AssetUpdateStep.RESTART:
      return t('unlock_flow.asset_update.progress.steps.restart');
    case AssetUpdateStep.SIGN_IN:
      return t('unlock_flow.asset_update.progress.steps.sign_in');
  }
}

const barColor = computed<'primary' | 'success' | 'error'>(() => {
  if (get(failed))
    return 'error';
  return get(done) ? 'success' : 'primary';
});

const errorReport = computed<string>(() => [error, get(range)].filter(Boolean).join('\n'));
const { copied, copy } = useCopy(errorReport);
</script>

<template>
  <StageLayout
    :data-outcome="failed ? 'failed' : (done ? 'done' : 'running')"
    data-testid="asset-update-progress"
  >
    <template #title>
      {{ title }}
    </template>
    <template #subtitle>
      {{ range }}
    </template>

    <RuiCard
      variant="outlined"
      no-padding
      class="overflow-hidden"
    >
      <div class="p-4">
        <RuiProgress
          :color="barColor"
          :variant="failed || done ? 'determinate' : 'indeterminate'"
          :value="100"
          :aria-label="title"
        />
      </div>
      <div class="border-t border-default px-4 py-3">
        <ul
          class="flex flex-col ml-2 pl-3 border-l border-default"
          :aria-label="t('unlock_flow.asset_update.progress.steps.label')"
        >
          <li
            v-for="row in steps"
            :key="row.step"
            class="flex items-center gap-2.5 py-1 text-body-2"
            :data-status="row.status"
            data-testid="asset-update-step"
          >
            <StageStepIcon :status="row.status" />
            <span
              class="flex-1 min-w-0 truncate"
              :class="{
                'font-medium': row.status === StageStepStatus.CURRENT,
                'text-rui-text-secondary': row.status === StageStepStatus.DONE || row.status === StageStepStatus.PENDING,
                'text-rui-error font-medium': row.status === StageStepStatus.FAILED,
              }"
            >
              {{ stepLabel(row.step) }}
            </span>
          </li>
        </ul>
      </div>
    </RuiCard>

    <div
      v-if="!failed && !done"
      class="flex gap-3 text-body-2 text-rui-text-secondary"
    >
      <RuiIcon
        name="lu-shield-check"
        size="20"
        class="shrink-0 mt-0.5 text-rui-primary"
      />
      <div class="flex flex-col gap-2">
        <p>{{ t('unlock_flow.asset_update.progress.keep_open') }}</p>
        <p
          v-if="automatic"
          data-testid="asset-update-automatic"
        >
          {{ t('unlock_flow.asset_update.progress.automatic') }}
        </p>
      </div>
    </div>

    <div
      v-else-if="failed"
      class="flex flex-col gap-4"
      data-testid="asset-update-failure"
    >
      <RuiAlert
        v-if="error"
        type="error"
      >
        <span
          class="break-words"
          data-testid="asset-update-error"
        >
          {{ error }}
        </span>
      </RuiAlert>
      <p class="text-body-2 text-rui-text-secondary">
        {{ t('unlock_flow.asset_update.progress.next_steps') }}
      </p>
    </div>

    <template
      v-if="failed"
      #actions
    >
      <RuiButton
        color="primary"
        data-testid="asset-update-back"
        @click="emit('back')"
      >
        {{ t('unlock_flow.asset_update.progress.actions.back') }}
      </RuiButton>
      <RuiButton
        v-if="error"
        variant="outlined"
        color="primary"
        data-testid="asset-update-copy"
        @click="startPromise(copy())"
      >
        <template #prepend>
          <RuiIcon
            :name="copied ? 'lu-check' : 'lu-copy'"
            size="16"
          />
        </template>
        {{ copied ? t('unlock_flow.asset_update.progress.actions.copied') : t('unlock_flow.asset_update.progress.actions.copy') }}
      </RuiButton>
      <RuiButton
        variant="text"
        color="primary"
        data-testid="asset-update-report"
        @click="emit('report')"
      >
        {{ t('unlock_flow.asset_update.progress.actions.report') }}
      </RuiButton>
    </template>
  </StageLayout>
</template>
