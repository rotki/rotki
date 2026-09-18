import { describe, expect, it } from 'vitest';
import { withProtocolCacheFrame } from './protocol-cache-activity';

const curve = { chain: 'ethereum', processed: 2, protocol: 'curve', total: 8 };
const aave = { chain: 'ethereum', processed: 1, protocol: 'aave', total: 4 };

describe('withProtocolCacheFrame', () => {
  it('should start the rows from the first frame', () => {
    expect(withProtocolCacheFrame([], curve)).toStrictEqual([curve]);
  });

  it('should put a new pair first and count the pair before it as full', () => {
    expect(withProtocolCacheFrame([curve], aave)).toStrictEqual([aave, { ...curve, processed: 8 }]);
  });

  it('should update a pair in place rather than adding it twice', () => {
    expect(withProtocolCacheFrame([curve], { ...curve, processed: 5 })).toStrictEqual([{ ...curve, processed: 5 }]);
  });

  it('should tell the same protocol on two chains apart', () => {
    const onOptimism = { ...curve, chain: 'optimism' };

    expect(withProtocolCacheFrame([curve], onOptimism)).toStrictEqual([onOptimism, { ...curve, processed: 8 }]);
  });

  it('should leave out a pair that reports no work', () => {
    expect(withProtocolCacheFrame([curve], { ...aave, processed: 0, total: 0 })).toStrictEqual([{ ...curve, processed: 8 }]);
  });

  it('should keep only the row fields of a websocket frame', () => {
    const frame = { ...curve, subtype: 'protocol_cache_updates' };

    expect(withProtocolCacheFrame([], frame)).toStrictEqual([curve]);
  });
});
