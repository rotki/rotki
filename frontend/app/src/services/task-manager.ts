import i18n from '@/i18n';
import { Task, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { api } from '@/services/rotkehlchen-api';
import { ActionResult, TaskNotFoundError } from '@/services/types-api';
import store from '@/store/store';
import { TaskMap } from '@/store/tasks/state';
import { assert } from '@/utils/assertions';

const error: (task: Task<TaskMeta>, message?: string) => ActionResult<{}> = (
  task,
  error
) => ({
  result: {},
  message: i18n
    .t('task_manager.error', {
      taskId: task.id,
      title: task.meta.title,
      error
    })
    .toString()
});

class TaskManager {
  private isRunning: boolean = false;

  private locked(): number[] {
    return store.state.tasks!.locked;
  }

  private tasks(): TaskMap<TaskMeta> {
    return store.state.tasks!.tasks;
  }

  private noTasks(): boolean {
    return Object.keys(this.tasks()).length === 0;
  }

  private remove(id: number) {
    store.commit('tasks/remove', id);
  }

  private lock(id: number) {
    store.commit('tasks/lock', id);
  }

  private unlock(id: number) {
    store.commit('tasks/unlock', id);
  }

  private filterOutUnprocessable(taskIds: number[]): number[] {
    const locked = this.locked();
    const tasks = this.tasks();
    return taskIds.filter(
      id => !locked.includes(id) || !tasks[id] || tasks[id].id === null
    );
  }

  monitor() {
    if (this.noTasks() || this.isRunning) {
      return;
    }

    this.isRunning = true;

    api
      .queryTasks()
      .then(({ completed }) =>
        this.handleTasks(this.filterOutUnprocessable(completed))
      )
      .finally(() => {
        this.isRunning = false;
      });
  }

  private async handleTasks(ids: number[]) {
    const tasks = this.tasks();
    return Promise.all(ids.map(id => this.processTask(tasks[id])));
  }

  private async processTask(task: Task<TaskMeta>) {
    this.lock(task.id);

    try {
      const result = await api.queryTaskResult(task.id, task.meta.numericKeys);
      assert(result !== null);
      this.handleResult(result, task);
    } catch (e) {
      if (e instanceof TaskNotFoundError) {
        this.remove(task.id);
        this.handleResult(error(task, e.message), task);
      }
    }
    this.unlock(task.id);
  }

  private handleResult(result: ActionResult<any>, task: Task<TaskMeta>) {
    if (task.meta.ignoreResult) {
      this.remove(task.id);
      return;
    }

    const handler =
      this.handler[task.type] ?? this.handler[`${task.type}-${task.id}`];

    if (!handler) {
      console.warn(`missing handler for ${task.type} with ${task.id}`);
      this.remove(task.id);
      return;
    }

    try {
      handler(result, task.meta);
    } catch (e) {
      handler(error(task, e.message), task.meta);
    }
    this.remove(task.id);
  }

  private handler: {
    [type: string]: (result: any, meta: any) => void;
  } = {};

  registerHandler<R, M extends TaskMeta>(
    task: TaskType,
    handlerImpl: (actionResult: ActionResult<R>, meta: M) => void,
    taskId?: string
  ) {
    const identifier = taskId ? `${task}-${taskId}` : task;
    this.handler[identifier] = handlerImpl;
  }

  unregisterHandler(task: TaskType, taskId?: string) {
    const identifier = taskId ? `${task}-${taskId}` : task;
    delete this.handler[identifier];
  }
}

export const taskManager = new TaskManager();
