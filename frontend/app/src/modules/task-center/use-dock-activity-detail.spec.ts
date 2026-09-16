import { afterEach, describe, expect, it } from 'vitest';
import { TransactionsQueryStatus } from '@/modules/core/messaging/types/status-types';
import { decodeActivity } from '@/modules/history/events/tx/decode-activity';
import { accountSyncActivity, chainSyncActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { protocolCacheActivity } from '@/modules/history/protocol-cache-activity';
import { type Activity, type ActivityId, ActivityKind, ActivitySourceType, ActivityStatus } from './core/types';
import { publishActivityDetail, useActivityDetail } from './use-activity-detail';
import { useDockActivityDetail } from './use-dock-activity-detail';

function activity(id: ActivityId, kind: ActivityKind, status: ActivityStatus = ActivityStatus.RUNNING): Activity {
  return {
    cancellable: true,
    id,
    kind,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: kind,
  };
}

const account = { address: '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1', chain: 'eth' };

describe('useDockActivityDetail', () => {
  afterEach(() => {
    useActivityDetail().resetDetails();
  });

  it('should name an account\'s current sub-query and the range it has reached', () => {
    publishActivityDetail(accountSyncActivity, account, {
      period: [1_600_000_000, 1_650_000_000],
      queryStep: TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS,
      windowEnd: 1_700_000_000,
    });

    const detail = useDockActivityDetail(activity(accountSyncActivity.id(account), ActivityKind.TX_SYNC));

    expect(get(detail)).toEqual({
      period: { from: 1_650_000_000, to: 1_700_000_000 },
      step: 'task_dock.detail.querying_internal',
      type: 'query',
    });
  });

  it('should mark a range that has not moved past its start as starting from the beginning', () => {
    publishActivityDetail(accountSyncActivity, account, {
      period: [1_600_000_000, 1_600_000_000],
      queryStep: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
    });

    const detail = get(useDockActivityDetail(activity(accountSyncActivity.id(account), ActivityKind.TX_SYNC)));

    expect(detail?.type === 'query' ? detail.period : undefined).toEqual({ from: undefined, to: 1_600_000_000 });
  });

  it('should give a chain row nothing, though its id prefixes its accounts\' ids', () => {
    publishActivityDetail(accountSyncActivity, account, { queryStep: TransactionsQueryStatus.QUERYING_TRANSACTIONS });

    const detail = useDockActivityDetail(activity(chainSyncActivity.id({ chain: 'eth' }), ActivityKind.TX_SYNC));

    expect(get(detail)).toBeUndefined();
  });

  it('should name the query an exchange is running', () => {
    const exchange = { location: 'kraken', name: 'main' };
    publishActivityDetail(exchangeEventsActivity, exchange, { eventType: 'trades', period: [1, 2] });

    const detail = useDockActivityDetail(activity(exchangeEventsActivity.id(exchange), ActivityKind.EXCHANGE_EVENTS));

    expect(get(detail)).toEqual({ period: { from: 1, to: 2 }, step: 'task_dock.detail.querying_event_type::Trades', type: 'query' });
  });

  it('should name the first protocol cache a decode is still filling, and count the rest', () => {
    const decoding = { chain: 'eth', ignoreCache: false };
    publishActivityDetail(decodeActivity, decoding, {
      protocols: [
        { chain: 'ethereum', processed: 44, protocol: 'aave', total: 44 },
        { chain: 'ethereum', processed: 18, protocol: 'curve', total: 44 },
        { chain: 'ethereum', processed: 0, protocol: 'yearn', total: 9 },
      ],
    });

    const detail = useDockActivityDetail(activity(decodeActivity.id(decoding), ActivityKind.TX_DECODING));

    expect(get(detail)).toEqual({
      current: { chain: 'ethereum', processed: 18, protocol: 'curve', total: 44 },
      more: 1,
      type: 'caches',
    });
  });

  it('should say nothing for a cache refresh whose caches are all full', () => {
    publishActivityDetail(protocolCacheActivity, undefined, { protocols: [{ chain: 'ethereum', processed: 5, protocol: 'curve', total: 5 }] });

    expect(get(useDockActivityDetail(activity(protocolCacheActivity.id(), ActivityKind.PROTOCOL_CACHE)))).toBeUndefined();
  });

  it('should say nothing once the activity has settled, whatever detail is left', () => {
    publishActivityDetail(accountSyncActivity, account, { queryStep: TransactionsQueryStatus.QUERYING_TRANSACTIONS });

    const detail = useDockActivityDetail(activity(accountSyncActivity.id(account), ActivityKind.TX_SYNC, ActivityStatus.COMPLETE));

    expect(get(detail)).toBeUndefined();
  });
});
