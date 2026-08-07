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
      <div
        v-if="expanded"
        class="flex flex-col pt-2 max-h-[50vh] overflow-y-auto"
      >
        <PendingTaskNode
          v-for="job in jobs"
          :key="job.activity.id"
          :activity="job.activity"
          :children="children"
          :now="now"
          class="border-t border-default py-1"
          @cancel="confirmCancel($event)"
        />
      </div>
    </RuiCard>
    <div v-else>
      <NoTasksRunning />
    </div>
  </div>
</template>
