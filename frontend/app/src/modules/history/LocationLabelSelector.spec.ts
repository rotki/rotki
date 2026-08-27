import type { LocationLabel } from '@/modules/core/common/location';
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

const address = '0x1234567890abcdef1234567890abcdef12345678';

const stubs = {
  AccountDisplay: true,
  EnsAvatar: true,
  LocationIcon: true,
  RuiAutoComplete: {
    props: ['classNames', 'options'],
    template: `<div data-testid="autocomplete" :data-menu-class="classNames?.menu">
      <slot />
      <template v-if="options.length > 0">
        <div data-testid="selection-slot"><slot name="selection" :item="options[0]" /></div>
        <div data-testid="item-slot"><slot name="item" :item="options[0]" /></div>
      </template>
    </div>`,
  },
  TagDisplay: true,
};

function createWrapper(options: LocationLabel[] = []): VueWrapper {
  return mount(LocationLabelSelector, {
    global: { stubs },
    props: { modelValue: '', options },
  });
}

describe('locationLabelSelector', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should constrain the dropdown menu to the field width, which the full address would otherwise stretch past it', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=autocomplete]').attributes('data-menu-class')).toBe('!min-w-full');
  });

  it('should render the selection compactly and the dropdown item in full, as the dense binding decides between them', () => {
    const wrapper = createWrapper([{ location: 'eth', locationLabel: address }]);

    expect(wrapper.find('[data-testid=selection-slot]').text()).toBe('0x1234...5678');
    expect(wrapper.find('[data-testid=item-slot]').text()).toBe('0x1234567890...ef12345678');
  });
});
