import { describe, expect, it } from 'vitest';
import {
  blockDecodeActivity,
  blockDecodeActivityId,
  decodeActivity,
  decodeActivityId,
  redecodeActivity,
  targetedDecodeActivity,
  targetedDecodeActivityId,
  targetedRedecodeActivity,
} from '@/modules/history/events/tx/decode.activity';

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

describe('redecode umbrella ids', () => {
  it('should give a redecode of everything its own id, absent or empty alike', () => {
    expect(redecodeActivity.id({})).toBe('redecode:all');
    expect(redecodeActivity.id({ chains: [] })).toBe('redecode:all');
  });

  it('should key a chain redecode by the sorted chain set, as one part', () => {
    expect(redecodeActivity.id({ chains: ['optimism', 'eth'] })).toBe('redecode:chains:eth,optimism');
  });

  it('should key a targeted redecode by its sorted members, and keep an empty one distinct from everything', () => {
    expect(targetedRedecodeActivity.id({ members: ['eth/0xb', 'block/7', 'eth/0xa'] })).toBe('redecode:targeted:block/7,eth/0xa,eth/0xb');
    expect(targetedRedecodeActivity.id({ members: [] })).toBe('redecode:targeted:');
    expect(targetedRedecodeActivity.id({ members: [] })).not.toBe(redecodeActivity.id({}));
  });
});
