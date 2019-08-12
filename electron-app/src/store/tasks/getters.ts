import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { TaskState } from '@/store/tasks/state';
import { TaskType } from '@/model/task';
import find from 'lodash/find';

export const getters: GetterTree<TaskState, RotkehlchenState> = {
  isTaskRunning: (state: TaskState) => (type: TaskType): boolean => {
    return !!find(state.tasks, item => item.type === type);
  }
};
