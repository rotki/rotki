import type { InteractionConnection, InteractionNode } from './address-interaction-graph';
import { describe, expect, it } from 'vitest';
import { counterpartOf, historyEventsRoute, sortByActivity } from './address-interaction-panel';

function node(id: string): InteractionNode {
  return { address: id, chains: ['eth'], id, x: 0, y: 0 };
}

function connection(id: string, txHashes: string[], source = node('a'), target = node('b')): InteractionConnection {
  return { chain: 'eth', id, source, target, txHashes };
}

describe('address interaction panel helpers', () => {
  it('should order connections by shared transactions, breaking ties by id', () => {
    const sorted = sortByActivity([
      connection('c', ['0x1']),
      connection('a', ['0x1']),
      connection('b', ['0x1', '0x2', '0x3']),
    ]);
    expect(sorted.map(entry => entry.id)).toEqual(['b', 'a', 'c']);
  });

  it('should return the far side of a connection from either endpoint', () => {
    const entry = connection('x', ['0x1']);
    expect(counterpartOf(entry, 'a')?.id).toBe('b');
    expect(counterpartOf(entry, 'b')?.id).toBe('a');
    expect(counterpartOf(entry, 'z')).toBeUndefined();
    expect(counterpartOf(entry)).toBeUndefined();
  });

  it('should filter history events to every transaction of the connection', () => {
    expect(historyEventsRoute(['0x1', '0x2'])).toEqual({ name: '/history/events/', query: { txRefs: ['0x1', '0x2'] } });
  });
});
