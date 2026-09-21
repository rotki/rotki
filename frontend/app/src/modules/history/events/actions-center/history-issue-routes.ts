import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import type { ActionTarget } from '@/modules/core/action-center/types';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { HistoryIssueTarget } from '@/modules/history/events/actions-center/use-history-event-issues';
import type { DialogType } from '@/modules/history/events/dialog-types';
import { historyDialogQuery, historyDialogRoute, isRoutableDialogType } from '@/modules/history/events/use-history-events-dialog-routing';

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
 * The route that opens a dialog over the history events page the user is already on.
 *
 * @remarks
 * It keeps the page's own query, the table's filters, page and sort, and replaces the current entry,
 * so the dialog opens over the table as the user left it and back-navigation does not land on a copy.
 */
function dialogInPlace(type: DialogType, pageQuery: LocationQuery): RouteLocationRaw {
  const dialogQuery = isRoutableDialogType(type) ? historyDialogQuery(type) : {};
  return { name: '/history/events/', query: { ...pageQuery, ...dialogQuery }, replace: true };
}

/**
 * Turns a history row's target into one that works from any page.
 *
 * @remarks
 * A dialog only opens on the history events page, so from anywhere else the row navigates there with
 * the query that opens it. A dialog no query can open lands on the page itself.
 *
 * @param target - the target the history rows were built with
 * @param historyPageQuery - the current query when the user is on the history events page, which a
 * dialog then opens over instead of navigating away from
 */
export function toGlobalTarget(target: HistoryIssueTarget, historyPageQuery?: LocationQuery): ActionTarget {
  switch (target.kind) {
    case 'dialog':
      if (historyPageQuery)
        return { kind: 'route', to: dialogInPlace(target.options.type, historyPageQuery) };
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
