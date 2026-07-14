import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import LocationLabelSelector from '@/modules/history/LocationLabelSelector.vue';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    allTxChainsInfo: ref([{ id: 'eth' }]),
    getEvmChainName: (chain: string): string | undefined => chain === 'eth' ? 'ethereum' : undefined,
    matchChain: (location: string): string | undefined => location === 'eth' ? 'eth' : undefined,
  }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({ getAddressName: (): undefined => undefined }),
}));

const stubs = {
  AccountDisplay: true,
  LocationIcon: true,
  RuiAutoComplete: {
    props: ['menuClass', 'options'],
    template: '<div data-testid="autocomplete" :data-menu-class="menuClass"><slot /></div>',
  },
  TagDisplay: true,
};

function createWrapper(): VueWrapper {
  return mount(LocationLabelSelector, {
    global: { stubs },
    props: { modelValue: '', options: [] },
  });
}

describe('locationLabelSelector', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should constrain the dropdown menu to the field width', () => {
    // The full address is used as text-attr, so without this the menu auto-sizes to the address
    // length and overflows the field (see AssetSelect, which does the same).
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=autocomplete]').attributes('data-menu-class')).toBe('!min-w-full');
  });
});
