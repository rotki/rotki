import { computed } from '@vue/composition-api';
import { TaskType } from '@/model/task-type';
import { useStore } from '@/store/utils';

export const setupTaskStatus = () => {
  const store = useStore();
  const isTaskRunning = (type: TaskType) =>
    computed(() => store.getters['tasks/isTaskRunning'](type));
  return { isTaskRunning };
};
