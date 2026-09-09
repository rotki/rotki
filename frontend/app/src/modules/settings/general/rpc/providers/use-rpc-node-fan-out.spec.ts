import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { Blockchain } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRpcNodeFanOut } from '@/modules/settings/general/rpc/providers/use-rpc-node-fan-out';

const { readNodes } = vi.hoisted(() => ({ readNodes: vi.fn() }));

vi.mock('@/modules/settings/general/rpc/providers/use-rpc-nodes-by-chain', () => ({
  useRpcNodesByChain: (): Record<string, unknown> => ({ readNodes }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    getChainName: (chain: string): string => chain,
  }),
}));

const INFURA = 'https://mainnet.infura.io/v3/abcdef';
const CHAINS = [Blockchain.ETH, Blockchain.OPTIMISM, Blockchain.BASE, Blockchain.GNOSIS];

function infuraNode(endpoint: string): BlockchainRpcNode {
  return {
    active: true,
    blockchain: Blockchain.OPTIMISM,
    endpoint,
    identifier: 1,
    name: 'Infura',
    owned: true,
    weight: 0,
  };
}

async function enabledFanOut(
  endpoint = INFURA,
  name = '',
): Promise<ReturnType<typeof useRpcNodeFanOut>> {
  const fanOut = useRpcNodeFanOut(() => endpoint, () => name, () => Blockchain.ETH, () => CHAINS);
  set(fanOut.modelEnabled, true);
  await flushPromises();
  return fanOut;
}

describe('settings/general/rpc/providers/use-rpc-node-fan-out', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    readNodes.mockResolvedValue({ nodes: {}, unreadable: [] });
  });

  it('should read the other chains as soon as a provider is recognised', async () => {
    const fanOut = useRpcNodeFanOut(() => INFURA, () => '', () => Blockchain.ETH, () => CHAINS);
    await flushPromises();

    expect(readNodes).toHaveBeenCalledOnce();
    expect(get(fanOut.candidates)).toHaveLength(2);
    expect(get(fanOut.modelEnabled)).toBe(false);
  });

  it('should read nothing for an endpoint it does not recognise', async () => {
    useRpcNodeFanOut(() => 'https://eth.example/rpc', () => '', () => Blockchain.ETH, () => CHAINS);
    await flushPromises();

    expect(readNodes).not.toHaveBeenCalled();
  });

  it('should leave out the chain the form is already adding', async () => {
    const fanOut = await enabledFanOut();

    expect(readNodes).toHaveBeenCalledWith([Blockchain.OPTIMISM, Blockchain.BASE, Blockchain.GNOSIS]);
    expect(get(fanOut.candidates).map(candidate => candidate.chain)).not.toContain(Blockchain.ETH);
  });

  it('should name the chains the provider does not serve', async () => {
    const fanOut = await enabledFanOut();

    expect(get(fanOut.unsupportedNames)).toContain(Blockchain.GNOSIS);
    expect(get(fanOut.candidates).map(candidate => candidate.chain)).toEqual([Blockchain.OPTIMISM, Blockchain.BASE]);
  });

  it('should tick every chain that has nothing on this key yet', async () => {
    readNodes.mockResolvedValue({
      nodes: { [Blockchain.OPTIMISM]: [infuraNode('https://optimism-mainnet.infura.io/v3/abcdef')] },
      unreadable: [],
    });

    const fanOut = await enabledFanOut();

    expect(get(fanOut.selected)).toEqual([Blockchain.BASE]);
    expect(get(fanOut.chosen)).toHaveLength(1);
  });

  it('should drop a chain the user unticks', async () => {
    const fanOut = await enabledFanOut();
    fanOut.toggle(Blockchain.BASE, false);

    expect(get(fanOut.selected)).toEqual([Blockchain.OPTIMISM]);
    expect(get(fanOut.chosen).map(candidate => candidate.chain)).toEqual([Blockchain.OPTIMISM]);
  });

  it('should name the chains whose nodes could not be read', async () => {
    readNodes.mockResolvedValue({ nodes: {}, unreadable: [Blockchain.BASE] });

    const fanOut = await enabledFanOut();

    expect(get(fanOut.unreadableNames)).toContain(Blockchain.BASE);
    expect(get(fanOut.candidates).map(candidate => candidate.chain)).toEqual([Blockchain.OPTIMISM]);
  });

  it('should carry the key, so a message quoting the endpoint can be masked', async () => {
    const fanOut = await enabledFanOut();

    expect(get(fanOut.credential)).toBe('abcdef');
  });

  it('should say what the provider needs switched on for the key', async () => {
    const fanOut = await enabledFanOut();

    expect(get(fanOut.enablementNote)).toContain('enablement.per_network');
  });

  it('should recognise nothing in an endpoint of another shape', () => {
    const fanOut = useRpcNodeFanOut(() => 'https://eth.example/rpc', () => '', () => Blockchain.ETH, () => CHAINS);

    expect(get(fanOut.provider)).toBeUndefined();
    expect(get(fanOut.enablementNote)).toBe('');
  });
});
