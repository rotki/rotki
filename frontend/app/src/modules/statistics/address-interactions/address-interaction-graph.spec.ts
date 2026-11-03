import type { AddressInteraction } from './address-interaction-types';
import { describe, expect, it } from 'vitest';
import { createAddressInteractionGraph, touches, transactionsOn } from './address-interaction-graph';

const A = '0xaaaa';
const B = '0xbbbb';
const C = '0xcccc';

function interaction(chain: string, txHash: string, source = A, target = B): AddressInteraction {
  return { chain, source, target, txHash };
}

describe('address interaction graph model', () => {
  it('should fold every chain of an unordered pair into one connection', () => {
    const graph = createAddressInteractionGraph([
      interaction('optimism', '0x3'),
      interaction('eth', '0x1'),
      interaction('eth', '0x2', B, A),
      interaction('eth', '0x1', B, A),
    ]);

    expect(graph.connections).toHaveLength(1);
    const [connection] = graph.connections;
    expect(connection.activity).toEqual([
      { bridgeTxHashes: [], chain: 'eth', txHashes: ['0x1', '0x2'] },
      { bridgeTxHashes: [], chain: 'optimism', txHashes: ['0x3'] },
    ]);
    expect(connection.txCount).toBe(3);
  });

  it('should count the same hash on two chains as two transactions', () => {
    const [connection] = createAddressInteractionGraph([interaction('eth', '0x1'), interaction('optimism', '0x1')]).connections;

    expect(connection.txCount).toBe(2);
  });

  it('should put each bridge leg under its own chain and each address on its endpoint chain', () => {
    const graph = createAddressInteractionGraph([
      { chain: 'eth', source: B, target: A, targetChain: 'optimism', targetTxHash: '0xwithdrawal', txHash: '0xdeposit' },
    ]);

    const [connection] = graph.connections;
    expect(connection.activity).toEqual([
      { bridgeTxHashes: ['0xdeposit'], chain: 'eth', txHashes: ['0xdeposit'] },
      { bridgeTxHashes: ['0xwithdrawal'], chain: 'optimism', txHashes: ['0xwithdrawal'] },
    ]);
    expect(connection.txCount).toBe(2);
    expect(graph.nodes.find(node => node.id === B)?.chains).toEqual(['eth']);
    expect(graph.nodes.find(node => node.id === A)?.chains).toEqual(['optimism']);
  });

  it('should deduplicate a repeated bridge and fold it with ordinary transfers of the same pair', () => {
    const bridge = { ...interaction('eth', '0xdeposit'), targetChain: 'optimism', targetTxHash: '0xwithdrawal' };
    const [connection] = createAddressInteractionGraph([bridge, bridge, interaction('eth', '0x1')]).connections;

    expect(connection.activity).toEqual([
      { bridgeTxHashes: ['0xdeposit'], chain: 'eth', txHashes: ['0x1', '0xdeposit'] },
      { bridgeTxHashes: ['0xwithdrawal'], chain: 'optimism', txHashes: ['0xwithdrawal'] },
    ]);
  });

  it('should flag only the pairs a matched bridge links', () => {
    const graph = createAddressInteractionGraph([
      interaction('eth', '0x1', A, C),
      { ...interaction('eth', '0xdeposit', B, A), targetChain: 'optimism', targetTxHash: '0xwithdrawal' },
    ]);

    expect(graph.connections.map(({ isBridge, source, target }) => [source.id, target.id, isBridge])).toEqual([
      [A, B, true],
      [A, C, false],
    ]);
  });

  it('should skip an address interacting with itself', () => {
    const graph = createAddressInteractionGraph([interaction('eth', '0x1', A, A), interaction('eth', '0x2', B, C)]);

    expect(graph.nodes.map(node => node.id)).toEqual([B, C]);
  });

  it('should record every chain an address appears on', () => {
    const graph = createAddressInteractionGraph([interaction('optimism', '0x1'), interaction('eth', '0x2', B, C)]);

    expect(graph.nodes.find(node => node.id === B)?.chains).toEqual(['eth', 'optimism']);
  });

  it('should tell whether a connection has the address at either end', () => {
    const [connection] = createAddressInteractionGraph([interaction('eth', '0x1')]).connections;

    expect([touches(connection, A), touches(connection, B), touches(connection, C), touches(connection)]).toEqual([true, true, false, false]);
  });

  it('should count transactions on one chain, or on all of them', () => {
    const [connection] = createAddressInteractionGraph([interaction('eth', '0x1'), interaction('eth', '0x2'), interaction('optimism', '0x3')]).connections;

    expect(transactionsOn(connection)).toBe(3);
    expect(transactionsOn(connection, 'eth')).toBe(2);
    expect(transactionsOn(connection, 'gnosis')).toBe(0);
  });

  it('should build the same graph whatever order the history comes in', () => {
    const interactions = [interaction('eth', '0x1'), interaction('optimism', '0x2'), interaction('eth', '0x3', B, C)];

    expect(createAddressInteractionGraph(interactions)).toEqual(createAddressInteractionGraph([...interactions].reverse()));
  });
});
