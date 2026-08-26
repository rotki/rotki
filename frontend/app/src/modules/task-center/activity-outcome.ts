import type { RuiIcons } from '@rotki/ui-library';
import { type MessageKey, msg } from '@/message-key';
import { type ActivityStatus, ActivityStatus as Status } from './core/types';

/** RUI chip colours, narrowed to the five a status can take. */
type OutcomeColor = 'error' | 'warning' | 'success' | 'grey' | 'primary';

export interface ActivityOutcome {
  readonly color: OutcomeColor;
  readonly key: MessageKey;
  /**
   * Named here rather than in the template, so the plugin's source scan cannot see it — every
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
 * Every status has an entry, RUNNING included: a running row shows the percentage ring only when
 * there is a percentage, and the orchestrator reports `-1` unless a producer counted steps.
 *
 * The settled statuses all need saying, including the two the progress rollup counts as done
 * (`projection.ts` `percentageOf`) — a subtree at 100% with two failed chains is otherwise
 * indistinguishable from a clean one.
 *
 * Kept out of the component so the mapping is assertable without mounting, and out of `core/`
 * because `msg.$t` is what makes the key-usage lint count these keys.
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
