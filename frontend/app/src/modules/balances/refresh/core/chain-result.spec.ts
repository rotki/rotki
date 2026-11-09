import { describe, expect, it } from 'vitest';
import { ChainResultDecision, type ChainResultFacts, decideChainResult } from './chain-result';

const FRESH: ChainResultFacts = { failed: false, isTargeted: false, olderThanStored: false, overtaken: false };

describe('decideChainResult', () => {
  it.each<[string, Partial<ChainResultFacts>, ChainResultDecision]>([
    ['apply a fresh result', {}, ChainResultDecision.APPLY],
    ['apply a fresh targeted result', { isTargeted: true }, ChainResultDecision.APPLY],
    ['refuse a result older than the chain holds', { olderThanStored: true }, ChainResultDecision.REFUSE_OLDER],
    ['forget earlier success when a full refresh fails', { failed: true }, ChainResultDecision.FORGET_EARLIER],
    ['keep earlier success when a targeted refresh fails', { failed: true, isTargeted: true }, ChainResultDecision.KEEP_EARLIER],
    ['drop an overtaken result', { overtaken: true }, ChainResultDecision.DROP_OVERTAKEN],
    ['drop an overtaken failure rather than forget the result that overtook it', { failed: true, overtaken: true }, ChainResultDecision.DROP_OVERTAKEN],
    ['drop an overtaken result that is also older', { olderThanStored: true, overtaken: true }, ChainResultDecision.DROP_OVERTAKEN],
    ['report a failure as a failure even when the facts call it older', { failed: true, olderThanStored: true }, ChainResultDecision.FORGET_EARLIER],
  ])('should %s', (_title, facts, expected) => {
    expect(decideChainResult({ ...FRESH, ...facts })).toBe(expected);
  });
});
