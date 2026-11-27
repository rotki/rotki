/** Where one step of a login stage's checklist stands, which picks its icon. */
export const StageStepStatus = {
  DONE: 'done',
  CURRENT: 'current',
  FAILED: 'failed',
  PENDING: 'pending',
} as const;

export type StageStepStatus = (typeof StageStepStatus)[keyof typeof StageStepStatus];
