import type { RouteLocationRaw } from 'vue-router';
import type { StakingInfo, useStakingPage } from '@/pages/staking/use-staking-page';
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
  { id: 'eth2', image: '/images/protocols/ethereum.svg', name: 'Eth2' },
  { id: 'liquity', image: '/images/protocols/liquity.png', name: 'Liquity' },
  { id: 'kraken', image: '/images/protocols/kraken.svg', name: 'Kraken' },
  { id: 'lido-csm', image: '/images/protocols/lido_csm.svg', name: 'Lido CSM' },
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
          FullSizeContent: { template: '<div data-testid="empty-state"><slot /></div>' },
          InternalLink: { props: ['to'], template: '<a data-testid="protocol-link"><slot /></a>' },
          RuiMenuSelect: { props: ['modelValue', 'options', 'label', 'keyAttr', 'textAttr'], template: '<div data-testid="location-select" />' },
        },
      },
      props: { location },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    pageState.hasPage = false;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should offer every staking location in the dropdown', () => {
    wrapper = mountPage();

    expect(wrapper.find('[data-testid=location-select]').exists()).toBe(true);
  });

  describe('with no location chosen', () => {
    it('should show the empty state rather than a staking page', () => {
      wrapper = mountPage();

      expect(wrapper.find('[data-testid=staking-picker]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=staking-page]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=empty-state]').exists()).toBe(true);
    });

    it('should offer a shortcut into each location', () => {
      wrapper = mountPage();

      expect(wrapper.findAll('[data-testid=protocol-link]')).toHaveLength(STAKING.length);
      expect(getRedirectLink).toHaveBeenCalledWith('eth2');
      expect(getRedirectLink).toHaveBeenCalledWith('lido-csm');
    });

    it('should show an image for each location', () => {
      wrapper = mountPage();

      expect(wrapper.findAll('[data-testid=protocol-image]').length).toBeGreaterThanOrEqual(STAKING.length);
    });
  });

  describe('with a location chosen', () => {
    beforeEach(() => {
      pageState.hasPage = true;
    });

    it('should render that page and drop the empty state', () => {
      wrapper = mountPage('kraken');

      expect(wrapper.find('[data-testid=staking-page]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=selected-staking-page]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=staking-picker]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=empty-state]').exists()).toBe(false);
    });

    it('should keep the dropdown available so another location can be chosen', () => {
      wrapper = mountPage('kraken');

      expect(wrapper.find('[data-testid=location-select]').exists()).toBe(true);
    });
  });
});
