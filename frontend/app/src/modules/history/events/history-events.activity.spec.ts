import { describe, expect, it } from 'vitest';
import {
  assetMovementMatchActivity,
  bridgeMatchActivity,
  historyEventsExportActivity,
  txLookupActivity,
  undecodedBreakdownActivity,
} from '@/modules/history/events/history-events.activity';
import { activityIdHasPrefix } from '@/modules/task-center/core/types';

const txHash = '0x7a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f9';

/** Literal ids on purpose, as in `decode.activity.spec.ts`. */
describe('history events activity ids', () => {
  it('should give the fixed operations their ids', () => {
    expect(undecodedBreakdownActivity.id()).toBe('history-events:undecoded');
    expect(historyEventsExportActivity.id()).toBe('history-events:export');
    expect(assetMovementMatchActivity.id()).toBe('history-events:match');
    expect(bridgeMatchActivity.id()).toBe('history-events:bridge');
  });

  it('should key a lookup by request and hash, so a newer lookup of one hash is a new request', () => {
    expect(txLookupActivity.id({ requestId: 3, txHash })).toBe(`history-events:lookup:3:${txHash}`);
    expect(txLookupActivity.id({ requestId: 4, txHash })).not.toBe(txLookupActivity.id({ requestId: 3, txHash }));
  });

  it('should keep every lookup under the prefix a newer one cancels by', () => {
    const within = txLookupActivity.partsWithin([]);
    expect(within).toStrictEqual(['lookup']);
    expect(activityIdHasPrefix(txLookupActivity.id({ requestId: 1, txHash }), txLookupActivity.kind, ...within)).toBe(true);
  });
});
