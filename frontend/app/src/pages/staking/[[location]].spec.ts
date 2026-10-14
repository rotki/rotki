import type { RouteLocationRaw } from 'vue-router';
import type { StakingInfo } from '@/pages/staking/use-staking-locations';
import type { useStakingPage } from '@/pages/staking/use-staking-page';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StakingPage from '@/pages/staking/[[location]].vue';

const getRedirectLink = vi.fn((location: string): RouteLocationRaw => ({
  name: '/staking/[[location]]',
  params: { location },
}));

const STAKING: StakingInfo[] = [
  { description: 'Validators, their rewards and withdrawals', id: 'eth2', image: '/images/protocols/ethereum.svg', name: 'ETH' },
  { description: 'Stability pool deposits', id: 'liquity', image: '/images/protocols/liquity.png', name: 'Liquity' },
  { description: 'Assets staked on the exchange', id: 'kraken', image: '/images/protocols/kraken.svg', name: 'Kraken' },
  { description: 'Node operator bonds', id: 'lido-csm', image: '/images/protocols/lido_csm.svg', name: 'Lido CSM' },
  { description: 'HYPE delegated to validators', id: 'hyperliquid', image: '/images/protocols/hyperliquid.svg', name: 'Hyperliquid' },
  { description: 'Stake accounts and their validators', id: 'solana', image: '/images/protocols/solana.svg', name: 'Solana' },
];

const pageState = vi.hoisted((): { hasPage: boolean } => ({ hasPage: false }));

vi.mock('@/pages/staking/use-staking-page', async () => {
  const { computed, defineComponent: defineComponentFn } = await import('vue');
  const selected = defineComponentFn({
    name: 'SelectedStakingPage',
    template: '<div data-testid="selected-staking-page" />',
  });
  return {
    useStakingPage: (): ReturnType<typeof useStakingPage> => ({
      getRedirectLink,
      modelLocation: computed({ get: () => undefined, set: () => {} }),
      page: computed(() => pageState.hasPage ? selected : null),
      staking: computed(() => STAKING),
    }),
  };
});

describe('pages/staking/[[location]]', () => {
  let wrapper: VueWrapper<InstanceType<typeof StakingPage>>;

  function mountPage(location: '' | 'kraken' = ''): VueWrapper<InstanceType<typeof StakingPage>> {
    return mount(StakingPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          AppImage: { props: ['src', 'size', 'fit'], template: '<div data-testid="protocol-image" />' },
          RouterLink: { props: ['to'], template: '<a v-bind="$attrs"><slot /></a>' },
          RuiTextField: {
            emits: ['update:modelValue'],
            props: ['modelValue'],
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
        },
      },
      props: { location },
    });
  }

  function cardLocations(): (string | undefined)[] {
    return wrapper.findAll('[data-testid=staking-location-card]').map(card => card.attributes('data-location'));
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    pageState.hasPage = false;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('with no location chosen', () => {
    it('should show a card for each location, linking to its page', () => {
      wrapper = mountPage();

      expect(wrapper.find('[data-testid=staking-page]').exists()).toBe(false);
      expect(cardLocations()).toEqual(STAKING.map(item => item.id));
      expect(getRedirectLink).toHaveBeenCalledWith('lido-csm');
      expect(wrapper.text()).toContain('Stake accounts and their validators');
    });

    it('should filter the cards by name', async () => {
      wrapper = mountPage();

      await wrapper.find('[data-testid=staking-location-filter]').setValue('sol');

      expect(cardLocations()).toEqual(['solana']);
    });

    it('should filter the cards by what a location tracks', async () => {
      wrapper = mountPage();

      await wrapper.find('[data-testid=staking-location-filter]').setValue('validators');

      expect(cardLocations()).toEqual(['eth2', 'hyperliquid', 'solana']);
    });

    it('should say so when nothing matches', async () => {
      wrapper = mountPage();

      await wrapper.find('[data-testid=staking-location-filter]').setValue('nothing like this');

      expect(cardLocations()).toEqual([]);
      expect(wrapper.find('[data-testid=staking-location-none]').exists()).toBe(true);
    });
  });

  describe('with a location chosen', () => {
    beforeEach(() => {
      pageState.hasPage = true;
    });

    it('should render that page instead of the cards', () => {
      wrapper = mountPage('kraken');

      expect(wrapper.find('[data-testid=selected-staking-page]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=staking-location-card]').exists()).toBe(false);
    });
  });
});
