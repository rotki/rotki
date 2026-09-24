<script setup lang="ts">
import DockJobNode from '@/modules/task-center/components/DockJobNode.vue';
import DockPanelHeader from '@/modules/task-center/components/DockPanelHeader.vue';
import DockPill from '@/modules/task-center/components/DockPill.vue';
import { DockState } from '@/modules/task-center/dock-state';
import { useCancelConfirmation } from '@/modules/task-center/use-cancel-confirmation';
import { useDockPanel } from '@/modules/task-center/use-dock-panel';
import { usePendingJobs } from '@/modules/task-center/use-pending-jobs';
import { useTaskController } from '@/modules/task-center/use-task-controller';
import { useTaskDock } from '@/modules/task-center/use-task-dock';

const { t } = useI18n({ useScope: 'global' });

const { acknowledge, holdInteraction, modelExpanded, state, visible } = useTaskDock();
const { children, jobs } = usePendingJobs();
const { canRetryAll, retryable, retryFailed, roots, sections, stoppable, summary, tally, title, total, unstoppable } = useDockPanel(jobs, children);
const { confirmCancel, confirmCancelAll } = useCancelConfirmation();
const { rerun } = useTaskController();

const now = useTimestamp({ interval: 1000 });

/** The panel needs a row to list; queued-only work keeps the pill but has nothing to expand into. */
const showPanel = computed<boolean>(() => get(modelExpanded) && get(roots).length > 0);

/** Reported outcomes stay until dismissed, failed or not; once dismissed they are only reopened. */
const isReporting = computed<boolean>(() => get(state) === DockState.FAILED || get(state) === DockState.ATTENTION || get(state) === DockState.DONE);

/**
 * A bulk action earns the footer only when it acts on more than one thing; with a single job, a
 * single failure or a single failure group, that row's own control does the same. Stop all counts
 * only the jobs it may safely interrupt.
 */
const canStopAll = computed<boolean>(() => get(stoppable).length > 1);

function toggle(): void {
  set(modelExpanded, !get(modelExpanded));
}
</script>

<template>
  <div
    v-if="visible"
    class="fixed bottom-4 right-4 z-[7] flex flex-col items-end gap-2 max-w-[calc(100vw-2rem)]"
    @mouseenter="holdInteraction(true)"
    @mouseleave="holdInteraction(false)"
    @focusin="holdInteraction(true)"
    @focusout="holdInteraction(false)"
  >
    <RuiCard
      v-if="showPanel"
      dense
      class="w-[25rem] max-w-full flex flex-col gap-2 shadow-lg"
      data-testid="task-dock-panel"
    >
      <DockPanelHeader
        :title="title"
        :summary="summary"
        :tally="tally"
        :total="total"
        @collapse="modelExpanded = false"
      />
      <div
        class="flex flex-col max-h-[50vh] overflow-y-auto -mx-1 px-1 divide-y divide-rui-grey-200 dark:divide-rui-grey-800"
        data-testid="dock-sections"
      >
        <div
          v-for="section in sections"
          :key="section.key"
          class="flex flex-col"
        >
          <div
            v-if="section.title"
            class="pt-2 pb-1 text-xs font-medium uppercase tracking-wide text-rui-text-secondary"
            data-testid="dock-section-title"
          >
            {{ section.title }}
          </div>
          <div class="flex flex-col divide-y divide-rui-grey-200 dark:divide-rui-grey-800">
            <DockJobNode
              v-for="root in section.roots"
              :key="root.id"
              :activity="root"
              :children="children"
              :now="now"
              :dismissible="isReporting"
              @cancel="confirmCancel($event)"
              @dismiss="acknowledge($event.id)"
              @retry="rerun($event)"
            />
          </div>
        </div>
      </div>
      <div
        v-if="canStopAll || canRetryAll"
        class="flex justify-end border-t border-default pt-2"
      >
        <RuiButton
          v-if="canRetryAll"
          variant="text"
          color="primary"
          size="sm"
          data-testid="dock-retry-failed"
          @click="retryFailed()"
        >
          {{ t('task_dock.panel.retry_failed', { count: retryable.length }, retryable.length) }}
        </RuiButton>
        <RuiButton
          v-else
          variant="text"
          color="primary"
          size="sm"
          data-testid="dock-stop-all"
          @click="confirmCancelAll(stoppable, unstoppable.length)"
        >
          {{ t('task_dock.panel.stop_all') }}
        </RuiButton>
      </div>
    </RuiCard>

    <DockPill
      :jobs="jobs"
      :children="children"
      :expanded="showPanel"
      @toggle="toggle()"
    />
  </div>
</template>
