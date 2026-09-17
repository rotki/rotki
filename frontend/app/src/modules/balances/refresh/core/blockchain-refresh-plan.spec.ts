import { describe, expect, it } from 'vitest';
import { planBlockchainRefresh } from './blockchain-refresh-plan';

const detectable = new Set<string>(['eth', 'optimism']);

function supportsDetection(chain: string): boolean {
  return detectable.has(chain);
}

describe('planBlockchainRefresh', () => {
  it('should query every chain when not redetecting', () => {
    expect(planBlockchainRefresh({ chains: ['eth', 'btc'], redetect: false, supportsDetection }))
      .toEqual({ detect: [], query: ['eth', 'btc'] });
  });

  it('should detect the chains detection covers and query the rest when redetecting', () => {
    expect(planBlockchainRefresh({ chains: ['eth', 'btc', 'optimism', 'solana'], redetect: true, supportsDetection }))
      .toEqual({ detect: ['eth', 'optimism'], query: ['btc', 'solana'] });
  });

  it('should never put a chain in both lists', () => {
    const { detect, query } = planBlockchainRefresh({ chains: ['eth', 'eth', 'btc'], redetect: true, supportsDetection });
    expect(detect.filter(chain => query.includes(chain))).toEqual([]);
    expect(detect).toEqual(['eth']);
  });

  it('should plan nothing for no chains', () => {
    expect(planBlockchainRefresh({ chains: [], redetect: true, supportsDetection }))
      .toEqual({ detect: [], query: [] });
  });
});
