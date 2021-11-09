import { computed } from '@vue/composition-api';
import { Task, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { useStore } from '@/store/utils';

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
