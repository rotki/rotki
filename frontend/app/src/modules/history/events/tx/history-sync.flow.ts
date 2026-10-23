import type { Exchange } from '@/modules/balances/types/exchanges';
import type { BankConnectionIdentity } from '@/modules/banks/types';
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import type { FlowChild, HistoryFlow } from '@/modules/history/events/flows';
import type { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import type { ActivityId } from '@/modules/task-center/core/types';
import { groupBy } from 'es-toolkit';
import { msg } from '@/message-key';
import {
  bankEventsActivity,
  bankEventsActivityId,
  chainSyncActivity,
  chainSyncActivityId,
  exchangeEventsActivity,
  exchangeEventsActivityId,
  historySyncActivity,
  onlineEventsActivity,
  onlineEventsActivityId,
} from '@/modules/history/events/tx/sync.activity';

/**
 * What a history refresh is made of, as data.
 *
 * The three kinds of work it fans out to, discriminated so the producer can dispatch on them
 * without re-deriving the shape it was handed.
 */
export type RefreshWork =
  | { readonly type: 'chain'; readonly chain: string; readonly accounts: ChainAddress[] }
  | { readonly type: 'exchange'; readonly exchange: Exchange }
  | { readonly type: 'bank'; readonly bank: BankConnectionIdentity }
  | { readonly type: 'online'; readonly query: OnlineHistoryEventsQueryType };

/** The resolved set a refresh covers — the scope its children are derived from. */
export interface RefreshScope {
  readonly accounts: ChainAddress[];
  readonly exchanges: Exchange[];
  readonly banks: BankConnectionIdentity[];
  readonly queries: OnlineHistoryEventsQueryType[];
}

/**
 * Pull everything new: transactions per tracked account, events per connected exchange and bank
 * connection, and the online event queries that belong to no chain.
 *
 * Singleton by identity — one refresh at a time, and `submitTask` dedup is what enforces that from
 * every surface, including callers in other modules that button-state guarding cannot reach.
 * Unlike a re-decode it deletes nothing, so it needs no exclusion against matching.
 *
 * Its re-entrancy branch and teardown deliberately live in the producer, not here: a declaration
 * describes the work, and `run` is the only place teardown can happen.
 */
export const historySyncFlow: HistoryFlow<RefreshScope, RefreshWork> = {
  /**
   * Heterogeneous, and grouped here rather than inside the sync: one child per chain (the unit a
   * user thinks in, and the group its per-account syncs and its decode hang from), one per
   * exchange, one per online query.
   *
   * Conditionality has already happened — the scope is the resolved target set, so a child that
   * may or may not turn out to exist cannot appear in this list.
   */
  children: (scope: RefreshScope): readonly FlowChild<RefreshWork>[] => [
    ...Object.entries(groupBy(scope.accounts, account => account.chain)).map(([chain, accounts]) => ({
      id: chainSyncActivityId(chain),
      kind: chainSyncActivity.kind,
      payload: { accounts, chain, type: 'chain' } as const,
    })),
    ...scope.exchanges.map(exchange => ({
      id: exchangeEventsActivityId(exchange.location, exchange.name),
      kind: exchangeEventsActivity.kind,
      payload: { exchange, type: 'exchange' } as const,
    })),
    ...scope.banks.map(bank => ({
      id: bankEventsActivityId(bank.location, bank.name),
      kind: bankEventsActivity.kind,
      payload: { bank, type: 'bank' } as const,
    })),
    ...scope.queries.map(query => ({
      id: onlineEventsActivityId(query),
      kind: onlineEventsActivity.kind,
      payload: { query, type: 'online' } as const,
    })),
  ],
  id: (): ActivityId => historySyncActivity.id(),
  kind: historySyncActivity.kind,
  titleKey: msg.$t('task_center.group.history_sync'),
};
