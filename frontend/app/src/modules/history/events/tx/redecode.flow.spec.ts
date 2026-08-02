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
    // The regression this guards: a scoped redecode that identified itself as `redecode:all` was
    // deduped by submitTask onto a concurrent full run and handed back that run's promise.
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
    // The point of declaring children: the shape of the run is assertable here, with no composable
    // mounted, no orchestrator and no backend.
    expect(redecodeFlow.children(['ethereum', 'optimism'])).toStrictEqual([
      { id: 'tx-decoding:ethereum', kind: ActivityKind.TX_DECODING, payload: 'ethereum' },
      { id: 'tx-decoding:optimism', kind: ActivityKind.TX_DECODING, payload: 'optimism' },
    ]);
  });

  it('should declare no children for an empty scope', () => {
    expect(redecodeFlow.children([])).toStrictEqual([]);
  });

  it('should name its children with the same constructor the mechanism submits under', () => {
    // Drift here does not fail loudly — the children simply stop being gated by their parent.
    const [child] = redecodeFlow.children(['ethereum']);
    expect(child.id).toBe(decodeActivityId('ethereum'));
  });

  it('should keep the chain set recoverable as a single id part', () => {
    // Comma-joined, not separator-joined: `activityParts` must read the set as one part rather
    // than shredding it into members.
    expect(activityParts(redecodeFlow.id(['ethereum', 'optimism']))).toStrictEqual(['chains', 'ethereum,optimism']);
  });
});
