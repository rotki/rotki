<script setup lang="ts">
import type { Activity } from '@/modules/task-center/core/types';
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { pnlReportActivity } from '@/modules/reports/reports.activity';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { useTaskController } from '@/modules/task-center/use-task-controller';

const { t } = useI18n({ useScope: 'global' });

/**
 * Whether the page is asking to confirm a stop. The question sits in place of the button, so it
 * goes away with the work: once the report settles there is nothing left to stop.
 */
const confirmingStop = ref<boolean>(false);

const { useActivity } = useTaskCenter();
const { cancel } = useTaskController();

const reportActivity = useActivity(pnlReportActivity.kind, ...pnlReportActivity.partsOf());

function stopGeneration(activity: Activity): void {
  set(confirmingStop, false);
  startPromise(cancel(activity));
}

watch(() => get(reportActivity)?.cancellable, (cancellable) => {
  if (!cancellable)
    set(confirmingStop, false);
});
</script>

<template>
  <div
    v-if="reportActivity?.cancellable"
    class="flex justify-center mt-6"
  >
    <div
      v-if="confirmingStop"
      class="flex items-center gap-1 pl-3 rounded-sm bg-rui-warning/10"
      data-testid="report-generation-stop-confirm"
    >
      <span class="text-sm">{{ t('task_dock.panel.stop_confirm') }}</span>
      <RuiButton
        variant="text"
        size="sm"
        data-testid="report-generation-keep-running"
        @click="confirmingStop = false"
      >
        {{ t('task_dock.panel.keep_running') }}
      </RuiButton>
      <RuiButton
        variant="text"
        color="error"
        size="sm"
        data-testid="report-generation-stop"
        @click="stopGeneration(reportActivity)"
      >
        {{ t('task_dock.panel.stop') }}
      </RuiButton>
    </div>
    <RuiButton
      v-else
      variant="outlined"
      data-testid="report-generation-cancel"
      @click="confirmingStop = true"
    >
      <template #prepend>
        <RuiIcon name="lu-circle-stop" />
      </template>
      {{ t('profit_loss_report.cancel_generation') }}
    </RuiButton>
  </div>
</template>
