import type { ChainInfo } from '@/modules/core/api/types/chains';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import HistoryRedecodeSelection from '@/modules/history/redecode/HistoryRedecodeSelection.vue';
import '@test/i18n';

const decodableTxChainsInfo = ref<ChainInfo[]>([]);

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ decodableTxChainsInfo }),
}));

const RuiMenu = {
  name: 'RuiMenu',
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
};

const ChainItem = {
  name: 'HistoryRedecodeChainItem',
  props: ['modelValue', 'disabled', 'chain'],
  template: '<div data-testid="chain-item" />',
};

const RuiCheckbox = {
  name: 'RuiCheckbox',
  props: ['modelValue', 'indeterminate', 'disabled'],
  template: '<button data-testid="select-all"><slot /></button>',
};

function evmChain(id: string, name: string): ChainInfo {
  return { evmChainName: id, id, image: '', name, type: 'evm' };
}

function nonEvmChain(id: string, name: string): ChainInfo {
  return { id, image: '', name, type: 'substrate' };
}

function createWrapper(): VueWrapper {
  return mount(HistoryRedecodeSelection, {
    global: { stubs: { HistoryRedecodeChainItem: ChainItem, RuiCheckbox, RuiMenu } },
    props: { loading: false },
  });
}

function offeredChains(wrapper: VueWrapper): string[] {
  return wrapper.findAllComponents({ name: 'HistoryRedecodeChainItem' }).map(item => item.props('chain'));
}

describe('historyRedecodeSelection', () => {
  it('should offer every decodable chain, not only the evm ones, so selecting all is the full run', async () => {
    set(decodableTxChainsInfo, [evmChain('ethereum', 'Ethereum'), nonEvmChain('polkadot', 'Polkadot')]);

    const wrapper = createWrapper();
    await nextTick();

    expect(offeredChains(wrapper)).toStrictEqual(['ethereum', 'polkadot']);
  });

  it('should select every offered chain at once, which is what marks a request as the full run', async () => {
    set(decodableTxChainsInfo, [evmChain('ethereum', 'Ethereum'), nonEvmChain('polkadot', 'Polkadot')]);

    const wrapper = createWrapper();
    await nextTick();

    await wrapper.find('[data-testid=select-all]').trigger('click');
    await nextTick();

    const selected = wrapper.findAllComponents({ name: 'HistoryRedecodeChainItem' })
      .filter(item => item.props('modelValue') === true)
      .map(item => item.props('chain'));

    expect(selected).toStrictEqual(['ethereum', 'polkadot']);
  });

  it('should match a chain on its evm name as well as its display name', async () => {
    set(decodableTxChainsInfo, [evmChain('polygon_pos', 'Polygon PoS'), nonEvmChain('polkadot', 'Polkadot')]);

    const wrapper = createWrapper();
    await nextTick();

    await wrapper.findComponent({ name: 'RuiTextField' }).setValue('polygon_pos');
    await nextTick();

    expect(offeredChains(wrapper)).toStrictEqual(['polygon_pos']);
  });
});
