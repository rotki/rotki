import { describe, expect, it } from 'vitest';
import { decodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { redecodeFlow } from '@/modules/history/events/tx/redecode.flow';
import { ActivityKind, activityParts } from '@/modules/task-center/core/types';

describe('redecodeFlow', () => {
  it('should give an unscoped run the canonical id', () => {
    expect(redecodeFlow.id()).toBe('redecode:all');
    expect(redecodeFlow.id([])).toBe('redecode:all');
  });

  it('should keep a scoped run distinct from the full one', () => {
    expect(redecodeFlow.id(['ethereum'])).not.toBe(redecodeFlow.id());
  });

  it('should give the same id to the same set in any order', () => {
    expect(redecodeFlow.id(['optimism', 'ethereum'])).toBe(redecodeFlow.id(['ethereum', 'optimism']));
  });

  it('should keep different sets apart', () => {
    expect(redecodeFlow.id(['ethereum'])).not.toBe(redecodeFlow.id(['optimism']));
    expect(redecodeFlow.id(['ethereum'])).not.toBe(redecodeFlow.id(['ethereum', 'optimism']));
  });

  it('should declare one decode child per chain, in the order given', () => {
    expect(redecodeFlow.children(['ethereum', 'optimism'])).toStrictEqual([
      { id: 'tx-decoding:ethereum:pull', kind: ActivityKind.TX_DECODING, payload: 'ethereum' },
      { id: 'tx-decoding:optimism:pull', kind: ActivityKind.TX_DECODING, payload: 'optimism' },
    ]);
  });

  it('should declare no children for an empty scope', () => {
    expect(redecodeFlow.children([])).toStrictEqual([]);
  });

  it('should name its children with the constructor the mechanism submits under, never the cached-decode identity', () => {
    const [child] = redecodeFlow.children(['ethereum']);
    expect(child.id).toBe(decodeActivityId('ethereum', true));
    expect(child.id).not.toBe(decodeActivityId('ethereum'));
  });

  it('should keep the chain set recoverable as a single id part', () => {
    expect(activityParts(redecodeFlow.id(['ethereum', 'optimism']))).toStrictEqual(['chains', 'ethereum,optimism']);
  });
});
