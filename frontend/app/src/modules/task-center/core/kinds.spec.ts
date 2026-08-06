import { describe, expect, it } from 'vitest';
import { groupTitle, kindRank } from './kinds';
import { type Activity, ActivitySourceType, ActivityStatus, ActivityKind as Kind, makeActivityId } from './types';

const t = (key: string): string => key;

describe('task-center kinds', () => {
  it('should rank blockchain balances ahead of prices ahead of other', () => {
    expect(kindRank(Kind.BLOCKCHAIN_BALANCES)).toBeLessThan(kindRank(Kind.PRICES));
    expect(kindRank(Kind.PRICES)).toBeLessThan(kindRank(Kind.OTHER));
  });

  it('should rank deferred kinds last (omitted from the table)', () => {
    const last = kindRank(Kind.OTHER) + 1;
    expect(kindRank(Kind.DB_UPGRADE)).toBe(last);
    expect(kindRank(Kind.DATA_MIGRATION)).toBe(last);
  });

  it('should resolve a static i18n group title for a known kind', () => {
    expect(groupTitle(Kind.PRICES, [], t)).toBe('task_center.group.prices');
    expect(groupTitle(Kind.SYNC, [], t)).toBe('task_center.group.sync');
  });

  it('should fall back to the first activity title for an unmapped kind', () => {
    const activity: Activity = {
      cancellable: false,
      id: makeActivityId(Kind.DB_UPGRADE, 'x'),
      kind: Kind.DB_UPGRADE,
      percentage: -1,
      rerunnable: false,
      source: { type: ActivitySourceType.NATIVE },
      status: ActivityStatus.RUNNING,
      title: 'Fallback title',
    };
    expect(groupTitle(Kind.DB_UPGRADE, [activity], t)).toBe('Fallback title');
  });
});
