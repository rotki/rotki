<script setup lang="ts">
import CollapsedPendingTasks from '@/modules/core/notifications/CollapsedPendingTasks.vue';
import NoTasksRunning from '@/modules/core/notifications/NoTasksRunning.vue';
import PendingTaskNode from '@/modules/core/notifications/PendingTaskNode.vue';
import { useCancelConfirmation } from '@/modules/task-center/use-cancel-confirmation';
import { usePendingJobs } from '@/modules/task-center/use-pending-jobs';

const expanded = defineModel<boolean>({ required: true });

const { children, jobs, percentage, steps } = usePendingJobs();
const { confirmCancel } = useCancelConfirmation();

// One timer for the whole panel; every row reads its elapsed time off it.
const now = useTimestamp({ interval: 1000 });

const hasJobs = computed<boolean>(() => get(jobs).length > 0);
</script>

<template>
  <div class="px-3.5 mb-2">
    <RuiCard
      v-if="hasJobs"
      dense
      class="flex flex-col gap-2"
    >
      <CollapsedPendingTasks
        v-model="expanded"
        :count="jobs.length"
        :steps="steps"
        :percentage="percentage"
      />
      <!--
        The rule separates one job from the next, so it goes between them rather than above each:
        a leading border drew a second line directly under the header's own divider. No padding
        here — every row owns its vertical space, so a job row and a nested row measure the same.
      -->
      <div
        v-if="expanded"
        class="flex flex-col divide-y divide-rui-grey-200 dark:divide-rui-grey-800 max-h-[50vh] overflow-y-auto"
      >
        <PendingTaskNode
          v-for="job in jobs"
          :key="job.activity.id"
          :activity="job.activity"
          :children="children"
          :now="now"
          @cancel="confirmCancel($event)"
        />
      </div>
    </RuiCard>
    <div v-else>
      <NoTasksRunning />
    </div>
  </div>
</template>
