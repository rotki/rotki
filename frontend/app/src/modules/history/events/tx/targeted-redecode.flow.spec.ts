import { describe, expect, it } from 'vitest';
import { blockDecodeActivityId, targetedDecodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { targetedRedecodeFlow } from '@/modules/history/events/tx/targeted-redecode.flow';
import { ActivityKind, activityParts } from '@/modules/task-center/core/types';

describe('targetedRedecodeFlow', () => {
  const ethereum = { chain: 'ethereum', txRefs: ['0xa', '0xb'] };

  it('should give the same id to the same request in any order', () => {
    const reversed = targetedRedecodeFlow.id({ blocks: [2, 1], byChain: [{ chain: 'ethereum', txRefs: ['0xb', '0xa'] }] });
    expect(reversed).toBe(targetedRedecodeFlow.id({ blocks: [1, 2], byChain: [ethereum] }));
  });

  it('should keep different requests apart', () => {
    // The regression this guards: the mechanism ids were scoped by chain alone (and the block one
    // was a bare singleton), so two different requests deduped onto each other and the second
    // caller was handed the first run's promise.
    const twoRefs = targetedRedecodeFlow.id({ blocks: [], byChain: [ethereum] });
    const oneRef = targetedRedecodeFlow.id({ blocks: [], byChain: [{ chain: 'ethereum', txRefs: ['0xa'] }] });
    expect(twoRefs).not.toBe(oneRef);

    const firstBlock = targetedRedecodeFlow.id({ blocks: [1], byChain: [] });
    expect(firstBlock).not.toBe(targetedRedecodeFlow.id({ blocks: [2], byChain: [] }));
  });

  it('should keep the same tx ref on different chains apart', () => {
    const onEthereum = targetedRedecodeFlow.id({ blocks: [], byChain: [{ chain: 'ethereum', txRefs: ['0xa'] }] });
    const onOptimism = targetedRedecodeFlow.id({ blocks: [], byChain: [{ chain: 'optimism', txRefs: ['0xa'] }] });
    expect(onEthereum).not.toBe(onOptimism);
  });

  it('should read the request as one part rather than shredding it', () => {
    // Comma-joined for the same reason the chain sweep does it: `activityParts` must recover the
    // set as a single member, not as one part per transaction.
    const parts = activityParts(targetedRedecodeFlow.id({ blocks: [], byChain: [ethereum] }));
    expect(parts).toHaveLength(2);
    expect(parts[1]).toBe('ethereum/0xa,ethereum/0xb');
  });

  it('should declare one decode per chain plus one for the blocks', () => {
    expect(targetedRedecodeFlow.children({ blocks: [7], byChain: [ethereum] })).toStrictEqual([
      {
        id: targetedDecodeActivityId('ethereum', ['0xa', '0xb']),
        kind: ActivityKind.TX_DECODING,
        payload: { chain: 'ethereum', txRefs: ['0xa', '0xb'], type: 'transactions' },
      },
      {
        id: blockDecodeActivityId([7]),
        kind: ActivityKind.ETH_BLOCK_DECODING,
        payload: { blockNumbers: [7], type: 'blocks' },
      },
    ]);
  });

  it('should not declare a block child when no blocks are requested', () => {
    const children = targetedRedecodeFlow.children({ blocks: [], byChain: [ethereum] });
    expect(children).toHaveLength(1);
    expect(children[0].kind).toBe(ActivityKind.TX_DECODING);
  });

  it('should declare children whose ids match what the mechanism submits', () => {
    // A declared id drifting from the submitted one would not fail loudly — the children would just
    // stop being gated by the parent that claims them.
    const [child] = targetedRedecodeFlow.children({ blocks: [], byChain: [ethereum] });
    expect(child.id).toBe(targetedDecodeActivityId('ethereum', ['0xb', '0xa']));
  });

  it('should reset, because a targeted redecode always deletes before re-deriving', () => {
    expect(targetedRedecodeFlow.resets).toBe(true);
  });
});
