/** How long the dismissed icon waits, collapsed and untouched, before the dock goes away. */
export const DISMISSED_HIDE_DELAY = 10_000;

export const DockState = {
  WORKING: 'working',
  /** The last run finished with nothing failed; shown until dismissed or a new run starts. */
  DONE: 'done',
  /** A settled job has a failure somewhere in its subtree; shown until dismissed. */
  FAILED: 'failed',
  /**
   * Everything reported has been dismissed; the pill shrinks to an icon that reopens it, and goes
   * away after {@link DISMISSED_HIDE_DELAY} collapsed with no interaction.
   */
  DISMISSED: 'dismissed',
} as const;

export type DockState = (typeof DockState)[keyof typeof DockState];
