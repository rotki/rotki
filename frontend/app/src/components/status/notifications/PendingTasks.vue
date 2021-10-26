<template>
  <div v-if="hasRunningTasks">
    <collapsed-pending-tasks v-model="expanded" :count="tasks.length" />
    <div v-if="expanded" class="pl-2" :class="$style.tasks">
      <pending-task v-for="task in tasks" :key="task.id" :task="task" />
    </div>
  </div>
  <div v-else>
    <no-tasks-running />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from '@vue/composition-api';
import CollapsedPendingTasks from '@/components/status/notifications/CollapsedPendingTasks.vue';
import NoTasksRunning from '@/components/status/notifications/NoTasksRunning.vue';
import PendingTask from '@/components/status/notifications/PendingTask.vue';
import { setupTaskStatus } from '@/composables/tasks';

export default defineComponent({
  name: 'PendingTasks',
  components: { NoTasksRunning, CollapsedPendingTasks, PendingTask },
  setup() {
    const expanded = ref(false);
    const { tasks, hasRunningTasks } = setupTaskStatus();
    return {
      tasks,
      hasRunningTasks,
      expanded
    };
  }
});
</script>

<style module lang="scss">
.tasks {
  padding-bottom: 4px;
}
</style>
