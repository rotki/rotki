import type { ActionResult } from '@rotki/common';
import type { CarriesFailureCause } from '@/modules/core/api/failure-cause';
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

/**
 * A finished task's result and message, with the status code the backend reported beside them. A
 * failed task also names its cause.
 */
export interface CompletedTaskOutcome<T> extends ActionResult<T>, CarriesFailureCause {
  statusCode?: number;
}

/** How one backend task reads its outcome, for the one whose failure is really a result. */
export interface RunTaskOptions {
  /**
   * A 409 hands back a result the caller acts on, instead of failing the task as any cause does.
   * Asset updates answer one with the conflicts the user has to resolve.
   */
  readonly conflictIsResult?: boolean;
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
