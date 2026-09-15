import type { RouteLocationRaw } from 'vue-router';
import type { ActionTarget } from '@/modules/core/action-center/types';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { HistoryIssueTarget } from '@/modules/history/events/actions-center/use-history-event-issues';
import { historyDialogRoute, isRoutableDialogType } from '@/modules/history/events/use-history-events-dialog-routing';

/** The events list filtered down to the duplicate groups a row names. */
export function duplicatesRoute(groupIds: string[], status: DuplicateHandlingStatus): RouteLocationRaw {
  return {
    name: '/history/events/',
    query: {
      duplicateHandlingStatus: status,
      groupIdentifiers: groupIds.join(','),
    },
  };
}

/**
 * Turns a history row's target into one that works from any page.
 *
 * @remarks
 * A dialog only opens on the history events page, so from anywhere else the row navigates there with
 * the query that opens it. A dialog no query can open lands on the page itself.
 */
export function toGlobalTarget(target: HistoryIssueTarget): ActionTarget {
  switch (target.kind) {
    case 'dialog':
      return {
        kind: 'route',
        to: isRoutableDialogType(target.options.type) ? historyDialogRoute(target.options.type) : { name: '/history/events/' },
      };
    case 'duplicates':
      return { kind: 'route', to: duplicatesRoute(target.groupIds, target.status) };
    case 'external':
    case 'pin':
    case 'route':
    case 'run':
      return target;
  }
}
