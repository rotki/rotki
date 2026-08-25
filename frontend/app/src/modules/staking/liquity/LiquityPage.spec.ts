import type { useLiquityPage } from '@/modules/staking/liquity/use-liquity-page';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import LiquityPage from '@/modules/staking/liquity/LiquityPage.vue';

const fetch = vi.fn(async (): Promise<void> => {});

const pageState = vi.hoisted((): { moduleEnabled: boolean; premium: boolean } => ({
  moduleEnabled: true,
  premium: true,
}));

const StakingDetailsStub = defineComponent({
  emits: ['refresh'],
  name: 'LiquityStakingDetailsStub',
  template: '<div data-testid="staking-details"><slot name="modules" /></div>',
});

const PlaceholderStub = defineComponent({
  name: 'LiquityStakingPagePlaceholderStub',
  props: { text: { default: '', type: String } },
  template: '<div data-testid="no-premium" />',
});

const ModuleNotActiveStub = defineComponent({
  name: 'ModuleNotActiveStub',
  props: { modules: { default: () => [], type: Array } },
  template: '<div data-testid="module-not-active" />',
});

vi.mock('@/modules/staking/liquity/use-liquity-page', async () => {
  const actual = await vi.importActual<typeof import('@/modules/staking/liquity/use-liquity-page')>(
    '@/modules/staking/liquity/use-liquity-page',
  );
  const { computed, shallowRef } = await import('vue');
  return {
    LIQUITY_MODULES: actual.LIQUITY_MODULES,
    useLiquityPage: (): ReturnType<typeof useLiquityPage> => ({
      fetch,
      moduleEnabled: computed(() => pageState.moduleEnabled),
      premium: shallowRef(pageState.premium),
    }),
  };
});

describe('modules/staking/liquity/LiquityPage', () => {
  let wrapper: VueWrapper<InstanceType<typeof LiquityPage>>;

  function mountPage(): VueWrapper<InstanceType<typeof LiquityPage>> {
    return mount(LiquityPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          ActiveModules: { props: ['modules'], template: '<div data-testid="active-modules" />' },
          LiquityStakingDetails: StakingDetailsStub,
          LiquityStakingPagePlaceholder: PlaceholderStub,
          ModuleNotActive: ModuleNotActiveStub,
        },
      },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    pageState.moduleEnabled = true;
    pageState.premium = true;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('without premium', () => {
    beforeEach(() => {
      pageState.premium = false;
    });

    it('should show only the upsell placeholder', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(PlaceholderStub).exists()).toBe(true);
      expect(wrapper.findComponent(StakingDetailsStub).exists()).toBe(false);
      expect(wrapper.findComponent(ModuleNotActiveStub).exists()).toBe(false);
    });

    it('should hand it the liquity copy, not another page\'s', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(PlaceholderStub).props('text')).toBe('liquity_page.no_premium');
    });

    it('should take precedence over the module being off', () => {
      pageState.moduleEnabled = false;

      wrapper = mountPage();

      expect(wrapper.findComponent(PlaceholderStub).exists()).toBe(true);
      expect(wrapper.findComponent(ModuleNotActiveStub).exists()).toBe(false);
    });
  });

  describe('with premium but the module off', () => {
    beforeEach(() => {
      pageState.moduleEnabled = false;
    });

    it('should ask for the module to be activated', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(ModuleNotActiveStub).exists()).toBe(true);
      expect(wrapper.findComponent(StakingDetailsStub).exists()).toBe(false);
    });

    it('should name the liquity module', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(ModuleNotActiveStub).props('modules')).toEqual(['liquity']);
    });
  });

  describe('with premium and the module on', () => {
    it('should show the staking details', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(StakingDetailsStub).exists()).toBe(true);
      expect(wrapper.findComponent(PlaceholderStub).exists()).toBe(false);
      expect(wrapper.findComponent(ModuleNotActiveStub).exists()).toBe(false);
    });

    it('should offer the module toggle in the details header', () => {
      wrapper = mountPage();

      expect(wrapper.find('[data-testid=active-modules]').exists()).toBe(true);
    });

    it('should refetch when the details ask for a refresh', () => {
      wrapper = mountPage();

      wrapper.findComponent(StakingDetailsStub).vm.$emit('refresh', true);

      expect(fetch).toHaveBeenCalledWith(true);
    });
  });
});
