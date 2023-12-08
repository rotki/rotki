<script setup lang="ts">
const expanded = ref(false);

const store = useTaskStore();
const { hasRunningTasks, tasks } = storeToRefs(store);
</script>

<template>
  <div class="px-3.5 mb-2">
    <RuiCard v-if="hasRunningTasks" class="flex flex-col gap-2">
      <CollapsedPendingTasks v-model="expanded" :count="tasks.length" />
      <div v-if="expanded" class="flex flex-col pt-4 -mb-4">
        <PendingTask
          v-for="task in tasks"
          :key="task.id"
          :task="task"
          class="border-t border-default py-4"
        />
      </div>
    </RuiCard>
    <div v-else>
      <NoTasksRunning />
    </div>
  </div>
</template>
