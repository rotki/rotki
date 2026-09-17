import { afterEach, describe, expect, it } from 'vitest';
import { decodeActivity } from '@/modules/history/events/tx/decode-activity';
import { buildTree } from './core/tree';
import { type Activity, type ActivityId, ActivityKind, ActivitySourceType, ActivityStatus, makeActivityId } from './core/types';
import { publishActivityDetail, useActivityDetail } from './use-activity-detail';
import { useJobBreakdown } from './use-job-breakdown';

function activity(id: ActivityId, kind: ActivityKind, status: ActivityStatus, parent?: ActivityId): Activity {
  return {
    cancellable: false,
    id,
    kind,
    parent,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: kind,
  };
}

const refresh = makeActivityId(ActivityKind.HISTORY_SYNC);
const eth = makeActivityId(ActivityKind.TX_SYNC, 'eth');
const gnosis = makeActivityId(ActivityKind.TX_SYNC, 'gnosis');
const ethDecode = decodeActivity.id({ chain: 'eth', ignoreCache: false });

function refreshTree(): Activity[] {
  return [
    activity(refresh, ActivityKind.HISTORY_SYNC, ActivityStatus.RUNNING),
    activity(eth, ActivityKind.TX_SYNC, ActivityStatus.COMPLETE, refresh),
    activity(makeActivityId(ActivityKind.TX_SYNC, 'eth', '0xa'), ActivityKind.TX_SYNC, ActivityStatus.COMPLETE, eth),
    activity(ethDecode, ActivityKind.TX_DECODING, ActivityStatus.COMPLETE, eth),
    activity(gnosis, ActivityKind.TX_SYNC, ActivityStatus.RUNNING, refresh),
    activity(makeActivityId(ActivityKind.TX_SYNC, 'gnosis', '0xb'), ActivityKind.TX_SYNC, ActivityStatus.RUNNING, gnosis),
    activity(makeActivityId(ActivityKind.EXCHANGE_EVENTS, 'kraken', 'main'), ActivityKind.EXCHANGE_EVENTS, ActivityStatus.RUNNING, refresh),
  ];
}

function breakdownOf(activities: Activity[]): { key: string; settled: number; total: number }[] {
  const { children, roots } = buildTree(activities, (a, b) => a.id.localeCompare(b.id));
  return get(useJobBreakdown(roots[0], children)).map(({ key, settled, total }) => ({ key, settled, total }));
}

describe('useJobBreakdown', () => {
  afterEach(() => {
    useActivityDetail().resetDetails();
  });

  it('should count each kind where it first appears, in kind order, so chains are counted and their accounts are not', () => {
    expect(breakdownOf(refreshTree())).toEqual([
      { key: ActivityKind.TX_SYNC, settled: 1, total: 2 },
      { key: ActivityKind.TX_DECODING, settled: 1, total: 1 },
      { key: ActivityKind.EXCHANGE_EVENTS, settled: 0, total: 1 },
    ]);
  });

  it('should count the protocol caches the job\'s decodes filled', () => {
    publishActivityDetail(decodeActivity, { chain: 'eth', ignoreCache: false }, {
      protocols: [
        { chain: 'ethereum', processed: 4, protocol: 'aave', total: 4 },
        { chain: 'ethereum', processed: 1, protocol: 'curve', total: 4 },
      ],
    });

    expect(breakdownOf(refreshTree()).at(-1)).toEqual({ key: ActivityKind.PROTOCOL_CACHE, settled: 1, total: 2 });
  });

  it('should flag a section with a failure beneath it as failed, and one with a cancellation as cancelled', () => {
    const tree = refreshTree();
    tree[2] = { ...tree[2], status: ActivityStatus.FAILED };
    tree[6] = { ...tree[6], status: ActivityStatus.CANCELLED };
    const { children, roots } = buildTree(tree, (a, b) => a.id.localeCompare(b.id));

    const problems = get(useJobBreakdown(roots[0], children)).map(({ key, problem }) => [key, problem]);

    expect(problems).toEqual([
      [ActivityKind.TX_SYNC, ActivityStatus.FAILED],
      [ActivityKind.TX_DECODING, undefined],
      [ActivityKind.EXCHANGE_EVENTS, ActivityStatus.CANCELLED],
    ]);
  });

  it('should flag the caches a settled decode left unfinished, but not those a running one is filling', () => {
    publishActivityDetail(decodeActivity, { chain: 'eth', ignoreCache: false }, {
      protocols: [{ chain: 'ethereum', processed: 1, protocol: 'curve', total: 4 }],
    });
    const { children, roots } = buildTree(refreshTree(), (a, b) => a.id.localeCompare(b.id));
    expect(get(useJobBreakdown(roots[0], children)).at(-1)?.problem).toBe(ActivityStatus.CANCELLED);

    const running = refreshTree();
    running[3] = { ...running[3], status: ActivityStatus.RUNNING };
    const live = buildTree(running, (a, b) => a.id.localeCompare(b.id));
    expect(get(useJobBreakdown(live.roots[0], live.children)).at(-1)?.problem).toBeUndefined();
  });

  it('should say nothing for a job of a single section', () => {
    expect(breakdownOf([
      activity(eth, ActivityKind.TX_SYNC, ActivityStatus.RUNNING),
      activity(makeActivityId(ActivityKind.TX_SYNC, 'eth', '0xa'), ActivityKind.TX_SYNC, ActivityStatus.RUNNING, eth),
    ])).toEqual([]);
  });
});
