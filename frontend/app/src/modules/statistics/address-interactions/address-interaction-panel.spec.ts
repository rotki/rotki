import type { ChainActivity, InteractionConnection, InteractionNode } from './address-interaction-graph';
import { describe, expect, it } from 'vitest';
import { counterpartOf, historyEventsRoute, sortByActivity } from './address-interaction-panel';

function node(id: string): InteractionNode {
  return { address: id, chains: ['eth'], id };
}

function connection(id: string, activity: ChainActivity[], source = node('a'), target = node('b')): InteractionConnection {
  return { activity, id, source, target, txCount: activity.reduce((sum, entry) => sum + entry.txHashes.length, 0) };
}

describe('address interaction panel helpers', () => {
  it('should order connections by shared transactions, keeping the incoming order for ties', () => {
    const sorted = sortByActivity([
      connection('a', [{ chain: 'eth', txHashes: ['0x1'] }]),
      connection('b', [{ chain: 'eth', txHashes: ['0x1', '0x2', '0x3'] }]),
      connection('c', [{ chain: 'eth', txHashes: ['0x1'] }]),
    ]);
    expect(sorted.map(entry => entry.id)).toEqual(['b', 'a', 'c']);
  });

  it('should order by the transactions on one chain when a chain is picked', () => {
    const sorted = sortByActivity([
      connection('busy', [{ chain: 'eth', txHashes: ['0x1', '0x2', '0x3'] }, { chain: 'optimism', txHashes: ['0x4'] }]),
      connection('quiet', [{ chain: 'optimism', txHashes: ['0x5', '0x6'] }]),
    ], 'optimism');
    expect(sorted.map(entry => entry.id)).toEqual(['quiet', 'busy']);
  });

  it('should return the far side of a connection from either endpoint', () => {
    const entry = connection('x', [{ chain: 'eth', txHashes: ['0x1'] }]);
    expect(counterpartOf(entry, 'a')?.id).toBe('b');
    expect(counterpartOf(entry, 'b')?.id).toBe('a');
    expect(counterpartOf(entry, 'z')).toBeUndefined();
    expect(counterpartOf(entry)).toBeUndefined();
  });

  it('should filter history events to every transaction of the connection on its own location', () => {
    expect(historyEventsRoute('ethereum', ['0x1', '0x2'])).toEqual({ name: '/history/events/', query: { location: 'ethereum', txRefs: ['0x1', '0x2'] } });
  });

  it('should leave the location filter off rather than send one the history page would not recognise', () => {
    expect(historyEventsRoute(undefined, ['0x1'])).toEqual({ name: '/history/events/', query: { txRefs: ['0x1'] } });
  });
});
