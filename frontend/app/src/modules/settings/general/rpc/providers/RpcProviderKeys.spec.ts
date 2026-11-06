import type { RpcProviderUsage } from '@/modules/settings/general/rpc/providers/rpc-provider-usage';
import { Blockchain } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import RpcProviderKeys from '@/modules/settings/general/rpc/providers/RpcProviderKeys.vue';

const { refresh, removeAll, usages } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return { refresh: vi.fn(), removeAll: vi.fn(), usages: shallowRef<RpcProviderUsage[]>([]) };
});

vi.mock('@/modules/settings/general/rpc/providers/use-rpc-provider-removal', async () => {
  const { ref } = await import('vue');
  return {
    useRpcProviderRemoval: (): Record<string, unknown> => ({
      refresh,
      removeAll,
      removing: ref<boolean>(false),
      usages,
    }),
  };
});

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

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = {
  emits: ['update:modelValue'],
  name: 'RuiMenu',
  props: ['modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
};

const CHIP = '[data-testid=provider-key-infura-dead…beef]';

function mountKeys(): VueWrapper {
  return mount(RpcProviderKeys, { global: { stubs: { RuiMenu } }, props: { chains: CHAINS } });
}

/** Clicks the chip's close button, then accepts the question it asks. */
async function removeChip(wrapper: VueWrapper): Promise<void> {
  await wrapper.find(`${CHIP} button`).trigger('click');
  await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');
  await flushPromises();
}

describe('settings/general/rpc/providers/RpcProviderKeys.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(usages, []);
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
    set(usages, [usage('infura', 'dead…beef', [Blockchain.ETH, Blockchain.OPTIMISM])]);

    const chip = mountKeys().find('[data-testid=provider-key-infura-dead…beef]');

    expect(chip.text()).toContain('remove.chip::2, Infura');
  });

  it('should tell two keys of one provider apart by naming them', () => {
    set(usages, [
      usage('infura', 'aaaa…aaaa', [Blockchain.ETH]),
      usage('infura', 'bbbb…bbbb', [Blockchain.OPTIMISM]),
    ]);

    const chips = mountKeys().findAll('[data-testid^=provider-key-infura]');

    expect(chips[0].text()).toContain('Infura aaaa…aaaa');
    expect(chips[1].text()).toContain('Infura bbbb…bbbb');
  });

  it('should leave the key off a provider with only one', () => {
    set(usages, [
      usage('infura', 'aaaa…aaaa', [Blockchain.ETH]),
      usage('alchemy', 'bbbb…bbbb', [Blockchain.OPTIMISM]),
    ]);

    const chips = mountKeys().findAll('[data-testid^=provider-key-]');

    expect(chips[0].text()).not.toContain('aaaa…aaaa');
  });

  it('should name every chain that loses a node beside the chip, before removing any', async () => {
    set(usages, [usage('infura', 'dead…beef', [Blockchain.ETH, Blockchain.OPTIMISM])]);
    const wrapper = mountKeys();

    await wrapper.find(`${CHIP} button`).trigger('click');

    expect(removeAll).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain(`${Blockchain.ETH}, ${Blockchain.OPTIMISM}`);
  });

  it('should remove nothing when the question is cancelled', async () => {
    set(usages, [usage('infura', 'dead…beef', [Blockchain.ETH])]);
    const wrapper = mountKeys();

    await wrapper.find(`${CHIP} button`).trigger('click');
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');
    await flushPromises();

    expect(removeAll).not.toHaveBeenCalled();
  });

  it('should remove the key, re-read the chains and report it upwards', async () => {
    set(usages, [usage('infura', 'dead…beef', [Blockchain.ETH])]);
    const wrapper = mountKeys();

    await removeChip(wrapper);

    expect(removeAll).toHaveBeenCalledWith(expect.objectContaining({ id: 'infura' }));
    expect(refresh).toHaveBeenCalledTimes(2);
    expect(wrapper.emitted('removed')).toHaveLength(1);
    expect(wrapper.find('[data-testid=provider-keys-remove-error]').exists()).toBe(false);
  });

  it('should say under the chips when only some of the nodes could be removed', async () => {
    removeAll.mockResolvedValue({ failed: 1, removed: 1 });
    set(usages, [usage('infura', 'dead…beef', [Blockchain.ETH, Blockchain.OPTIMISM])]);
    const wrapper = mountKeys();

    await removeChip(wrapper);

    const strip = wrapper.find('[data-testid=provider-keys-remove-error]');
    expect(strip.text()).toContain('rpc_provider_setup.remove.partial::1, Infura, 1');
    expect(wrapper.emitted('removed')).toHaveLength(1);
  });

  it('should retry a partial removal on the nodes the provider still holds', async () => {
    removeAll.mockResolvedValueOnce({ failed: 1, removed: 1 });
    set(usages, [usage('infura', 'dead…beef', [Blockchain.ETH, Blockchain.OPTIMISM])]);
    const wrapper = mountKeys();
    await removeChip(wrapper);
    const left = usage('infura', 'dead…beef', [Blockchain.OPTIMISM]);
    set(usages, [left]);

    await wrapper.find('[data-testid=failure-strip-retry]').trigger('click');
    await flushPromises();

    expect(removeAll).toHaveBeenLastCalledWith(left);
    expect(wrapper.find('[data-testid=provider-keys-remove-error]').exists()).toBe(false);
  });
});
