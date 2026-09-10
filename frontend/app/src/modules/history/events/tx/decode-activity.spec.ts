import { describe, expect, it } from 'vitest';
import {
  blockDecodeActivity,
  blockDecodeActivityId,
  decodeActivity,
  decodeActivityId,
  targetedDecodeActivity,
  targetedDecodeActivityId,
} from '@/modules/history/events/tx/decode-activity';

/**
 * The ids are asserted as literals on purpose. Comparing a helper against the descriptor it
 * delegates to holds whatever both produce, so a change to the id shape would pass while every
 * flow that names its children ahead of the mechanism silently stopped matching them.
 */
describe('decode activity ids', () => {
  it('should key a chain decode by chain and cache flag', () => {
    expect(decodeActivity.id({ chain: 'eth', ignoreCache: false })).toBe('tx-decoding:eth:cached');
    expect(decodeActivity.id({ chain: 'eth', ignoreCache: true })).toBe('tx-decoding:eth:pull');
  });

  it('should give a cached and a forced decode of one chain distinct ids', () => {
    expect(decodeActivity.id({ chain: 'eth', ignoreCache: false }))
      .not
      .toBe(decodeActivity.id({ chain: 'eth', ignoreCache: true }));
  });

  it('should key a targeted decode by chain and the sorted tx set', () => {
    expect(targetedDecodeActivity.id({ chain: 'eth', txRefs: ['0xb', '0xa'] })).toBe('tx-decoding:eth:pull:0xa,0xb');
  });

  it('should give two tx sets on one chain distinct ids', () => {
    expect(targetedDecodeActivity.id({ chain: 'eth', txRefs: ['0xa'] }))
      .not
      .toBe(targetedDecodeActivity.id({ chain: 'eth', txRefs: ['0xb'] }));
  });

  it('should key a block decode by the sorted block set', () => {
    expect(blockDecodeActivity.id({ blockNumbers: [21_000_001, 21_000_000] })).toBe('eth-block-decoding:21000000,21000001');
  });

  it('should leave a chain decode readable under a chain prefix', () => {
    const within = decodeActivity.partsWithin(['eth']);
    expect(within).toStrictEqual(['eth']);
    expect(decodeActivity.id({ chain: 'eth', ignoreCache: true }).startsWith(`tx-decoding:${within.join(':')}:`)).toBe(true);
  });

  it('should route every named helper through its descriptor', () => {
    expect(decodeActivityId('eth', true)).toBe(decodeActivity.id({ chain: 'eth', ignoreCache: true }));
    expect(decodeActivityId('eth')).toBe(decodeActivity.id({ chain: 'eth', ignoreCache: false }));
    expect(targetedDecodeActivityId('eth', ['0xa'])).toBe(targetedDecodeActivity.id({ chain: 'eth', txRefs: ['0xa'] }));
    expect(blockDecodeActivityId([7])).toBe(blockDecodeActivity.id({ blockNumbers: [7] }));
  });
});
