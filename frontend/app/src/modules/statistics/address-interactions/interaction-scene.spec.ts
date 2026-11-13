import type { AddressInteraction } from './address-interaction-types';
import { graphOf, sceneOf } from '@test/utils/address-interactions';
import { describe, expect, it } from 'vitest';
import { findPath } from './interaction-clusters';
import { InteractionFilterMode } from './interaction-filter-mode';
import { focusOf, type InteractionFilters, type InteractionScene } from './interaction-scene';

const graph = graphOf([
  { chain: 'eth', source: 'a', target: 'b', txHash: '0x1' },
  { chain: 'eth', source: 'a', target: 'b', txHash: '0x2' },
  { chain: 'optimism', source: 'b', target: 'c', txHash: '0x3' },
  { chain: 'eth', source: 'c', target: 'd', txHash: '0x4' },
] satisfies AddressInteraction[]);

const AB = JSON.stringify(['a', 'b']);
const BC = JSON.stringify(['b', 'c']);
const CD = JSON.stringify(['c', 'd']);

function scene(filters: Partial<InteractionFilters> = {}, hiddenIds?: ReadonlySet<string>): InteractionScene {
  return sceneOf(graph, filters, hiddenIds);
}

describe('interaction scene', () => {
  it('should keep a connection on another chain drawn but inactive', () => {
    const result = scene({ chain: 'optimism' });

    expect(result.connections.map(({ id }) => id)).toEqual([AB, BC, CD]);
    expect([...result.activeConnectionIds]).toEqual([BC]);
    expect([...result.activeNodeIds].sort()).toEqual(['b', 'c']);
  });

  it('should keep a connection that is not a matched bridge drawn but inactive when only bridges are wanted', () => {
    const bridged = sceneOf(graphOf([
      { chain: 'eth', source: 'a', target: 'b', txHash: '0x1' },
      { chain: 'eth', source: 'b', target: 'c', targetChain: 'optimism', targetTxHash: '0x2', txHash: '0x3' },
    ]), { bridges: InteractionFilterMode.ONLY });

    expect(bridged.connections).toHaveLength(2);
    expect([...bridged.activeConnectionIds]).toEqual([JSON.stringify(['b', 'c'])]);
    expect([...bridged.activeNodeIds].sort()).toEqual(['b', 'c']);
  });

  it('should treat a pair as a bridge only on the chains its bridge legs happened on', () => {
    const pair = graphOf([
      { chain: 'eth', source: 'a', target: 'b', targetChain: 'optimism', targetTxHash: '0x2', txHash: '0x1' },
      { chain: 'gnosis', source: 'a', target: 'b', txHash: '0x3' },
    ]);

    expect(sceneOf(pair, { bridges: InteractionFilterMode.ONLY, chain: 'optimism' }).activeConnectionIds.size).toBe(1);
    expect(sceneOf(pair, { bridges: InteractionFilterMode.ONLY, chain: 'gnosis' }).activeConnectionIds.size).toBe(0);
  });

  it('should filter shared deposits on the selected chain and combine with the bridge filter', () => {
    const pair = graphOf([
      { chain: 'eth', source: 'a', target: 'b', depositAddress: 'deposit', txHash: '0x1' },
      { chain: 'gnosis', source: 'a', target: 'b', txHash: '0x2' },
      { chain: 'eth', source: 'b', target: 'c', targetChain: 'optimism', targetTxHash: '0x4', txHash: '0x3' },
    ]);

    expect([...sceneOf(pair, { chain: 'eth', sharedDeposits: InteractionFilterMode.ONLY }).activeConnectionIds]).toEqual([AB]);
    expect(sceneOf(pair, { chain: 'gnosis', sharedDeposits: InteractionFilterMode.ONLY }).activeConnectionIds.size).toBe(0);
    expect(sceneOf(pair, { bridges: InteractionFilterMode.ONLY, sharedDeposits: InteractionFilterMode.ONLY }).activeConnectionIds.size).toBe(0);
  });

  it('should drop the pairs a filter describes when it is set to exclude', () => {
    const pair = graphOf([
      { chain: 'eth', source: 'a', target: 'b', depositAddress: 'deposit', txHash: '0x1' },
      { chain: 'eth', source: 'b', target: 'c', targetChain: 'optimism', targetTxHash: '0x4', txHash: '0x3' },
      { chain: 'eth', source: 'c', target: 'd', txHash: '0x5' },
    ]);

    expect([...sceneOf(pair, { bridges: InteractionFilterMode.EXCLUDE }).activeConnectionIds]).toEqual([AB, CD]);
    expect([...sceneOf(pair, { sharedDeposits: InteractionFilterMode.EXCLUDE }).activeConnectionIds]).toEqual([BC, CD]);
  });

  it('should keep a connection below the minimum drawn but inactive', () => {
    expect([...scene({ minTransactions: 2 }).activeConnectionIds]).toEqual([AB]);
  });

  it('should not draw a hidden address or any of its connections', () => {
    const result = scene({}, new Set(['b']));

    expect(result.nodes.map(({ id }) => id)).toEqual(['a', 'c', 'd']);
    expect(result.connections.map(({ id }) => id)).toEqual([CD]);
  });

  it('should focus a selected address on its active neighbours only', () => {
    const focus = focusOf(scene({ chain: 'eth' }), { nodeId: 'b' });

    expect([...(focus?.nodeIds ?? [])].sort()).toEqual(['a', 'b']);
    expect([...(focus?.connectionIds ?? [])]).toEqual([AB]);
  });

  it('should focus a path on its steps, and on both ends when they are not linked', () => {
    const drawn = scene();
    const path = findPath('a', 'd', drawn.connections);

    expect([...(focusOf(drawn, { nodeId: 'a', path, pathTargetId: 'd' })?.connectionIds ?? [])]).toEqual([AB, BC, CD]);
    expect([...(focusOf(drawn, { nodeId: 'a', pathTargetId: 'd' })?.nodeIds ?? [])]).toEqual(['a', 'd']);
  });

  it('should focus a cluster on its members and the connections between them', () => {
    const focus = focusOf(scene(), { clusterNodeIds: ['a', 'b'] });

    expect([...(focus?.connectionIds ?? [])]).toEqual([AB]);
  });

  it('should dim nothing while nothing is selected', () => {
    expect(focusOf(scene(), {})).toBeUndefined();
  });
});
