import { describe, expect, it } from 'vitest';
import { createAddressInteractionGraph } from './address-interaction-graph';
import { layoutInteractionGraph } from './interaction-layout';

const interactions = [
  { chain: 'eth', source: '0xa', target: '0xb', txHash: '0x1' },
  { chain: 'optimism', source: '0xa', target: '0xb', txHash: '0x2' },
  { chain: 'eth', source: '0xb', target: '0xc', txHash: '0x3' },
  { chain: 'eth', source: '0xd', target: '0xe', txHash: '0x4' },
];

describe('interaction layout', () => {
  it('should lay out the same graph identically every time, whatever the history order', () => {
    expect(layoutInteractionGraph(createAddressInteractionGraph(interactions)))
      .toEqual(layoutInteractionGraph(createAddressInteractionGraph([...interactions].reverse())));
  });

  it('should keep addresses far enough apart that avatars and labels do not overlap', () => {
    const positions = [...layoutInteractionGraph(createAddressInteractionGraph(interactions)).values()];

    for (const [index, a] of positions.entries()) {
      for (const b of positions.slice(index + 1))
        expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThan(60);
    }
  });
});
