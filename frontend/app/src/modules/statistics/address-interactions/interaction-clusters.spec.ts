import type { InteractionConnection } from './address-interaction-graph';
import { graphOf, links } from '@test/utils/address-interactions';
import { describe, expect, it } from 'vitest';
import { findClusters, findPath } from './interaction-clusters';

function link(source: string, target: string, transactions = 1): [string, string, number] {
  return [source, target, transactions];
}

function connectionsOf(...pairs: [string, string, number][]): InteractionConnection[] {
  return graphOf(links(...pairs)).connections;
}

function pair(connection?: InteractionConnection): string[] | undefined {
  return connection ? [connection.source.id, connection.target.id] : undefined;
}

describe('interaction clusters', () => {
  it('should group linked addresses, largest cluster first', () => {
    const clusters = findClusters(connectionsOf(link('x', 'y'), link('a', 'b'), link('b', 'c')));

    expect(clusters.map(cluster => cluster.nodeIds)).toEqual([['a', 'b', 'c'], ['x', 'y']]);
    expect(clusters.map(cluster => cluster.txCount)).toEqual([2, 1]);
  });

  it('should lead each cluster with its best-connected address', () => {
    const [cluster] = findClusters(connectionsOf(link('a', 'hub'), link('b', 'hub'), link('c', 'hub'), link('c', 'd')));

    expect(cluster.lead.id).toBe('hub');
  });

  it('should name the bridge with the fewest transactions as the weakest link', () => {
    const [cluster] = findClusters(connectionsOf(
      link('a', 'b', 5),
      link('b', 'c', 4),
      link('c', 'a', 3),
      link('c', 'd', 2),
      link('d', 'e', 1),
    ));

    expect(pair(cluster.weakestLink)).toEqual(['d', 'e']);
  });

  it('should skip a weak connection that sits on a cycle, since removing it splits nothing', () => {
    const [cluster] = findClusters(connectionsOf(
      link('a', 'b', 1),
      link('b', 'c', 9),
      link('c', 'a', 9),
      link('c', 'd', 4),
    ));

    expect(pair(cluster.weakestLink)).toEqual(['c', 'd']);
  });

  it('should report no weakest link when every connection sits on a cycle', () => {
    const [cluster] = findClusters(connectionsOf(link('a', 'b'), link('b', 'c'), link('c', 'a')));

    expect(cluster.weakestLink).toBeUndefined();
  });

  it('should handle a chain of addresses longer than the call stack is deep', () => {
    const chain = Array.from({ length: 20_000 }, (_, index) => `n${String(index).padStart(5, '0')}`);
    const [cluster] = findClusters(connectionsOf(...chain.slice(1).map((id, index) => link(chain[index], id))));

    expect(cluster.nodeIds).toHaveLength(20_000);
    expect(cluster.weakestLink).toBeDefined();
  });

  it('should find the shortest path between two linked addresses', () => {
    const connections = connectionsOf(link('a', 'b'), link('b', 'c'), link('c', 'd'), link('a', 'x'), link('x', 'd'));
    const path = findPath('a', 'd', connections);

    expect(path?.nodes.map(({ id }) => id)).toEqual(['a', 'x', 'd']);
    expect(path?.connections.map(pair)).toEqual([['a', 'x'], ['d', 'x']]);
  });

  it('should find no path between addresses in different clusters, or from an address to itself', () => {
    const connections = connectionsOf(link('a', 'b'), link('x', 'y'));

    expect(findPath('a', 'y', connections)).toBeUndefined();
    expect(findPath('a', 'a', connections)).toBeUndefined();
  });
});
