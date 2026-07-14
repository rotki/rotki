import { flushPromises } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useArchiveNodes } from '@/modules/history/balances/use-archive-nodes';

const nodesByChain: Record<string, { isArchive: boolean }[]> = {};

vi.mock('@/modules/settings/api/use-evm-nodes-api', () => ({
  useEvmNodesApi: (chain: string): object => ({
    fetchEvmNodes: async (): Promise<{ isArchive: boolean }[]> => {
      if (chain === 'fail')
        throw new Error('network');
      return nodesByChain[chain] ?? [];
    },
  }),
}));

describe('useArchiveNodes', () => {
  beforeEach(() => {
    nodesByChain.eth = [{ isArchive: false }, { isArchive: true }];
    nodesByChain.optimism = [{ isArchive: false }];
  });

  it('should flag only chains that have a connected archive node', async () => {
    const { hasArchiveNode, loading } = useArchiveNodes(ref(['eth', 'optimism']));
    await flushPromises();

    expect(get(loading)).toBe(false);
    expect(get(hasArchiveNode('eth'))).toBe(true);
    expect(get(hasArchiveNode('optimism'))).toBe(false);
    expect(get(hasArchiveNode(undefined))).toBe(false);
  });

  it('should treat a failed node lookup as no archive node', async () => {
    const { hasArchiveNode } = useArchiveNodes(ref(['fail']));
    await flushPromises();

    expect(get(hasArchiveNode('fail'))).toBe(false);
  });

  it('should re-resolve when the chain list changes', async () => {
    const chains = ref<string[]>([]);
    const { hasArchiveNode } = useArchiveNodes(chains);
    await flushPromises();

    expect(get(hasArchiveNode('eth'))).toBe(false);

    set(chains, ['eth']);
    await flushPromises();

    expect(get(hasArchiveNode('eth'))).toBe(true);
  });
});
