import type { RpcProviderCandidate } from '@/modules/settings/general/rpc/providers/rpc-provider-plan';
import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import RpcProviderFanOutOffer from '@/modules/settings/general/rpc/providers/RpcProviderFanOutOffer.vue';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    getChainName: (chain: string): string => chain,
  }),
}));

function candidate(chain: string, existing = false): RpcProviderCandidate {
  return {
    chain,
    endpoint: `https://${chain}.infura.io/v3/abcdef`,
    ...(existing
      ? { existing: { active: true, blockchain: chain, endpoint: 'e', identifier: 1, name: 'Infura', owned: true, weight: 0 } }
      : {}),
    name: 'Infura',
  };
}

function mountOffer(props: Record<string, unknown> = {}): VueWrapper {
  return mount(RpcProviderFanOutOffer, {
    global: { stubs: { ChainIcon: true } },
    props: {
      candidates: [candidate(Blockchain.OPTIMISM), candidate(Blockchain.BASE)],
      modelValue: false,
      provider: 'Infura',
      selected: [Blockchain.OPTIMISM, Blockchain.BASE],
      ...props,
    },
  });
}

describe('settings/general/rpc/providers/RpcProviderFanOutOffer.vue', () => {
  it('should offer the other chains without opting the user in', () => {
    const wrapper = mountOffer();

    expect(wrapper.find('[data-testid=provider-fan-out-offer]').text()).toContain('offer.hint');
    expect(wrapper.find('[data-testid=provider-fan-out-enable] input').element).toHaveProperty('checked', false);
    expect(wrapper.find('[data-testid=provider-chain-picker]').exists()).toBe(false);
  });

  it('should show the picker once the user opts in', () => {
    const wrapper = mountOffer({ modelValue: true });

    expect(wrapper.find('[data-testid=provider-selection-summary]').text()).toContain('select.picker::2, 2');
    expect(wrapper.findAll('[data-testid=provider-candidate]')).toHaveLength(2);
  });

  it('should count the selection once a chain is unticked', () => {
    const wrapper = mountOffer({ modelValue: true, selected: [Blockchain.OPTIMISM] });

    expect(wrapper.find('[data-testid=provider-selection-summary]').text()).toContain('select.picker::1, 2');
  });

  it('should report a chain it is unticking', async () => {
    const wrapper = mountOffer({ modelValue: true });

    await wrapper.findAll('[data-testid=provider-candidate] input[type=checkbox]')[0].setValue(false);

    expect(wrapper.emitted('toggle')?.[0]).toEqual([{ chain: Blockchain.OPTIMISM, checked: false }]);
  });

  it('should say so when every other chain already holds the key', () => {
    const wrapper = mountOffer({
      candidates: [candidate(Blockchain.OPTIMISM, true)],
      modelValue: true,
      selected: [],
    });

    expect(wrapper.find('[data-testid=provider-nothing-to-add]').text()).toContain('select.none');
    expect(wrapper.find('[data-testid=provider-chain-picker]').exists()).toBe(false);
  });

  it('should keep the picker back while the chains are being read', () => {
    const wrapper = mountOffer({ modelValue: true, preparing: true });

    expect(wrapper.find('[data-testid=provider-chain-picker]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=provider-nothing-to-add]').exists()).toBe(false);
  });
});
