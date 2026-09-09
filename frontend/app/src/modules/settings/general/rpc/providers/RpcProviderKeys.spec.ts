import type { RpcProviderUsage } from '@/modules/settings/general/rpc/providers/rpc-provider-usage';
import { Blockchain } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import RpcProviderKeys from '@/modules/settings/general/rpc/providers/RpcProviderKeys.vue';

const { confirm, refresh, removeAll, setMessage, usages } = vi.hoisted(() => {
  const usages: { value: RpcProviderUsage[] } = { value: [] };
  return { confirm: vi.fn(), refresh: vi.fn(), removeAll: vi.fn(), setMessage: vi.fn(), usages };
});

vi.mock('@/modules/settings/general/rpc/providers/use-rpc-provider-removal', async () => {
  const { computed, ref } = await import('vue');
  return {
    useRpcProviderRemoval: (): Record<string, unknown> => ({
      refresh,
      removeAll,
      removing: ref(false),
      usages: computed(() => usages.value),
    }),
  };
});

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show: confirm }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    getChainName: (chain: string): string => chain,
  }),
}));

function usage(id: 'infura' | 'alchemy', key: string, chains: string[]): RpcProviderUsage {
  return {
    id,
    key,
    name: id === 'infura' ? 'Infura' : 'Alchemy',
    nodes: chains.map((chain, index) => ({ chain, identifier: index + 1, name: 'node' })),
  };
}

const CHAINS = [Blockchain.ETH, Blockchain.OPTIMISM];

function mountKeys(): VueWrapper {
  return mount(RpcProviderKeys, { props: { chains: CHAINS } });
}

/** Runs what the confirmation would have run, without asserting on the dialog itself. */
async function acceptConfirmation(): Promise<void> {
  await confirm.mock.calls[0][1]();
  await flushPromises();
}

describe('settings/general/rpc/providers/RpcProviderKeys.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    usages.value = [];
    removeAll.mockResolvedValue({ failed: 0, removed: 2 });
  });

  it('should read the chains it is given', () => {
    mountKeys();

    expect(refresh).toHaveBeenCalledWith(CHAINS);
  });

  it('should render nothing while no provider key is in use', () => {
    expect(mountKeys().find('[data-testid=provider-keys]').exists()).toBe(false);
  });

  it('should name the provider and count its nodes', () => {
    usages.value = [usage('infura', 'dead…beef', [Blockchain.ETH, Blockchain.OPTIMISM])];

    const chip = mountKeys().find('[data-testid=provider-key-infura-dead…beef]');

    expect(chip.text()).toContain('remove.chip::2, Infura');
  });

  it('should tell two keys of one provider apart by naming them', () => {
    usages.value = [
      usage('infura', 'aaaa…aaaa', [Blockchain.ETH]),
      usage('infura', 'bbbb…bbbb', [Blockchain.OPTIMISM]),
    ];

    const chips = mountKeys().findAll('[data-testid^=provider-key-infura]');

    expect(chips[0].text()).toContain('Infura aaaa…aaaa');
    expect(chips[1].text()).toContain('Infura bbbb…bbbb');
  });

  it('should leave the key off a provider with only one', () => {
    usages.value = [
      usage('infura', 'aaaa…aaaa', [Blockchain.ETH]),
      usage('alchemy', 'bbbb…bbbb', [Blockchain.OPTIMISM]),
    ];

    const chips = mountKeys().findAll('[data-testid^=provider-key-]');

    expect(chips[0].text()).not.toContain('aaaa…aaaa');
  });

  it('should name every chain that loses a node before removing any', async () => {
    usages.value = [usage('infura', 'dead…beef', [Blockchain.ETH, Blockchain.OPTIMISM])];
    const wrapper = mountKeys();

    await wrapper.find('[data-testid=provider-key-infura-dead…beef] button').trigger('click');

    expect(removeAll).not.toHaveBeenCalled();
    expect(confirm.mock.calls[0][0].message).toContain(`${Blockchain.ETH}, ${Blockchain.OPTIMISM}`);
  });

  it('should remove the key, re-read the chains and report it upwards', async () => {
    usages.value = [usage('infura', 'dead…beef', [Blockchain.ETH])];
    const wrapper = mountKeys();

    await wrapper.find('[data-testid=provider-key-infura-dead…beef] button').trigger('click');
    await acceptConfirmation();

    expect(removeAll).toHaveBeenCalledWith(expect.objectContaining({ id: 'infura' }));
    expect(refresh).toHaveBeenCalledTimes(2);
    expect(wrapper.emitted('removed')).toHaveLength(1);
    expect(setMessage).not.toHaveBeenCalled();
  });

  it('should say so when only some of the nodes could be removed', async () => {
    removeAll.mockResolvedValue({ failed: 1, removed: 1 });
    usages.value = [usage('infura', 'dead…beef', [Blockchain.ETH, Blockchain.OPTIMISM])];
    const wrapper = mountKeys();

    await wrapper.find('[data-testid=provider-key-infura-dead…beef] button').trigger('click');
    await acceptConfirmation();

    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: false }));
    expect(wrapper.emitted('removed')).toHaveLength(1);
  });
});
