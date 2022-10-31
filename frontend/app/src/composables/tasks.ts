import { useTasks } from '@/store/tasks';

export const setupTaskStatus = () => {
  const store = useTasks();
  return {
    isTaskRunning: store.isTaskRunning,
    hasRunningTasks: computed(() => store.hasRunningTasks),
    tasks: computed(() => store.tasks)
  };
};
