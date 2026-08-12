import type { RuiIcons } from '@rotki/ui-library';
import { type MessageKey, msg } from '@/message-key';
import { type ActivityStatus, ActivityStatus as Status } from './core/types';

/** RUI chip colours, narrowed to the five a status can take. */
export type OutcomeColor = 'error' | 'warning' | 'success' | 'grey' | 'primary';

export interface ActivityOutcome {
  readonly color: OutcomeColor;
  readonly key: MessageKey;
  /**
   * ⚠️ Named here rather than in the template, so the plugin's source scan cannot see it — every
   * icon below has to be listed in `vite.config.ts` `ruiIconsPlugin.include` or it silently
   * renders as nothing.
   */
  readonly icon: RuiIcons;
  /**
   * **Filled means it needs your attention; outlined means it is expected.**
   *
   * Only FAILED is filled. A history refresh settles dozens of children successfully, and filling
   * those made a wall of green "Done" the loudest thing in the panel, drowning the one chain at 60%
   * and the one at 0%, which is the only part a reader is actually there for. A skip is expected
   * too: filled amber shouted over every neighbouring row for something nobody has to act on.
   */
  readonly variant: 'filled' | 'outlined';
}

/**
 * How a status reads on a row.
 *
 * Every status has an entry, RUNNING included. A running row only shows the percentage ring when
 * there is a percentage to show, and most rows have none — the orchestrator reports `-1` unless a
 * producer counted steps. The slot used to fall back to a spinner, which said nothing the ticking
 * elapsed time did not already say and added one more spinning thing to a screen that has plenty.
 *
 * The settled statuses are states the reader has to be told about — including the two the progress
 * rollup deliberately counts as done (`projection.ts` `percentageOf`), which is exactly why they
 * need saying. A subtree at 100% with two failed chains is otherwise indistinguishable from a
 * clean one.
 *
 * Kept out of the component so the mapping can be asserted without mounting anything, and out of
 * `core/` because it names i18n keys — `msg.$t` is what makes the key-usage lint count them.
 */
const OUTCOME: Record<ActivityStatus, ActivityOutcome> = {
  [Status.CANCELLED]: {
    color: 'grey',
    icon: 'lu-ban',
    key: msg.$t('pending_task.status.cancelled'),
    variant: 'outlined',
  },
  [Status.COMPLETE]: {
    color: 'success',
    icon: 'lu-check',
    key: msg.$t('pending_task.status.done'),
    variant: 'outlined',
  },
  [Status.FAILED]: {
    color: 'error',
    icon: 'lu-circle-x',
    key: msg.$t('pending_task.status.failed'),
    variant: 'filled',
  },
  [Status.PENDING]: {
    color: 'grey',
    icon: 'lu-clock',
    key: msg.$t('pending_task.status.queued'),
    variant: 'outlined',
  },
  [Status.RUNNING]: {
    color: 'primary',
    icon: 'lu-activity',
    key: msg.$t('pending_task.status.running'),
    variant: 'outlined',
  },
  [Status.SKIPPED]: {
    color: 'warning',
    icon: 'lu-skip-forward',
    key: msg.$t('pending_task.status.skipped'),
    variant: 'outlined',
  },
};

export function activityOutcome(status: ActivityStatus): ActivityOutcome {
  return OUTCOME[status];
}
