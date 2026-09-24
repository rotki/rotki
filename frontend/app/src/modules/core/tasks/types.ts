import type { ActionResult } from '@rotki/common';
import { z } from 'zod';

/**
 * A backend task the frontend is waiting on. The label is display-only: it names the task in the
 * monitor's failure notification and in the dev logs. Identity is the backend id.
 */
export interface Task {
  readonly id: number;
  readonly label: string;
}

export interface TaskResultResponse<T> {
  outcome: T | null;
  status: 'completed' | 'not-found' | 'pending';
  statusCode?: number;
}

/** A finished task's result and message, with the status code the backend reported beside them. */
export interface CompletedTaskOutcome<T> extends ActionResult<T> {
  statusCode?: number;
}

/** How one backend task reads its outcome, for the few whose failure still carries a result. */
export interface RunTaskOptions {
  /**
   * A 409 that carries a message is this task's failure, whatever result it holds. Not a default,
   * because asset updates answer a 409 with the conflicts the user has to resolve.
   */
  readonly conflictFails?: boolean;
}

export interface TaskStatus {
  readonly pending: number[];
  readonly completed: number[];
}

export type TaskMap = Record<number, Task>;

export class TaskNotFoundError extends Error {
  constructor(msg: string, options?: ErrorOptions) {
    super(msg, options);
    this.name = 'TaskNotFoundError';
  }
}

export const PendingTaskSchema = z.object({
  taskId: z.number(),
});

export type PendingTask = z.infer<typeof PendingTaskSchema>;
