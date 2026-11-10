import type { RouteLocationRaw } from 'vue-router';
import { FailureCause } from '@/modules/core/api/failure-cause';
import { type Activity, ActivityKind } from '@/modules/task-center/core/types';

/**
 * Where the credentials each kind of work authenticates with are edited. A kind is listed only when
 * every key it can be refused for lives on that one page, so the link never sends the user to the
 * wrong place.
 */
const CREDENTIAL_PAGES: Partial<Record<ActivityKind, RouteLocationRaw>> = {
  [ActivityKind.BANK_BALANCES]: { name: '/accounts/banks/' },
  [ActivityKind.BANK_EVENTS]: { name: '/accounts/banks/' },
  [ActivityKind.EXCHANGE_BALANCES]: { name: '/accounts/exchanges/' },
  [ActivityKind.EXCHANGE_EVENTS]: { name: '/accounts/exchanges/' },
  [ActivityKind.EXCHANGE_SAVINGS]: { name: '/accounts/exchanges/' },
  [ActivityKind.SYNC]: { name: '/api-keys/premium/' },
  [ActivityKind.TX_SYNC]: { name: '/api-keys/external/' },
};

/**
 * The page that fixes a failure, for one that only a changed key can fix.
 *
 * @remarks
 * A rejected key leaves no retry worth offering, so this is the row's way forward instead. Any other
 * cause gets nothing: a retry or the failure's own message already says what to do.
 */
export function fixRouteOf({ failureCause, kind }: Pick<Activity, 'failureCause' | 'kind'>): RouteLocationRaw | undefined {
  return failureCause === FailureCause.AUTH ? CREDENTIAL_PAGES[kind] : undefined;
}
