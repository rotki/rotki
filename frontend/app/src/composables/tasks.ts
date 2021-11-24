import { computed } from '@vue/composition-api';
import { useStore } from '@/store/utils';
import { Task, TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const setupTaskStatus = () => {
  const store = useStore();
  const isTaskRunning = (type: TaskType) => {
    return computed(() => store.getters['tasks/isTaskRunning'](type));
  };
  const hasRunningTasks = computed<boolean>(
    () => store.getters['tasks/hasRunningTasks']
  );
  const tasks = computed<Task<TaskMeta>[]>(() => store.getters['tasks/tasks']);
  return { isTaskRunning, hasRunningTasks, tasks };
};
