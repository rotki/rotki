<template>
  <div v-if="hasRunningTasks" class="pl-2">
    <pending-task v-for="task in tasks" :key="task.id" :task="task" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import PendingTask from '@/components/status/notifications/PendingTask.vue';
import { setupTaskStatus } from '@/composables/tasks';

export default defineComponent({
  name: 'PendingTasks',
  components: { PendingTask },
  setup() {
    const { tasks, hasRunningTasks } = setupTaskStatus();
    return {
      tasks,
      hasRunningTasks
    };
  }
});
</script>
