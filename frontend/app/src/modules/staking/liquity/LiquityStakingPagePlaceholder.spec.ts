import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import LiquityStakingPagePlaceholder from '@/modules/staking/liquity/LiquityStakingPagePlaceholder.vue';

const isMdAndDown = vi.hoisted(() => ({ current: false }));

vi.mock('@rotki/ui-library', async (importOriginal) => {
  const { computed } = await import('vue');
  return {
    ...(await importOriginal<typeof import('@rotki/ui-library')>()),
    useBreakpoint: (): Record<string, unknown> => ({ isMdAndDown: computed(() => isMdAndDown.current) }),
  };
});

const AppImageStub = defineComponent({
  name: 'AppImageStub',
  props: { src: { default: '', type: String } },
  template: '<img data-testid="placeholder-image" :src="src" >',
});

const UpsellStub = defineComponent({
  name: 'GetPremiumPlaceholderStub',
  props: { title: { default: '', type: String } },
  template: '<div data-testid="premium-upsell" />',
});

describe('modules/staking/liquity/LiquityStakingPagePlaceholder', () => {
  let wrapper: VueWrapper<InstanceType<typeof LiquityStakingPagePlaceholder>>;

  function mountComponent(): VueWrapper<InstanceType<typeof LiquityStakingPagePlaceholder>> {
    return mount(LiquityStakingPagePlaceholder, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          AppImage: AppImageStub,
          GetPremiumPlaceholder: UpsellStub,
        },
      },
      props: { text: 'the liquity copy' },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    isMdAndDown.current = false;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should show the premium upsell over the preview images', () => {
    wrapper = mountComponent();

    expect(wrapper.find('[data-testid=premium-upsell]').exists()).toBe(true);
    expect(wrapper.findAllComponents(AppImageStub)).toHaveLength(3);
  });

  it('should show the copy it was given, rather than another page\'s', () => {
    wrapper = mountComponent();

    expect(wrapper.findComponent(UpsellStub).props('title')).toBe('the liquity copy');
  });

  it('should use the wide statistics preview on a large screen', () => {
    wrapper = mountComponent();

    const sources = wrapper.findAllComponents(AppImageStub).map(item => item.props('src') ?? '');
    expect(sources.some(src => src.includes('liquity_staking_statistics.png'))).toBe(true);
    expect(sources.some(src => src.includes('_mobile'))).toBe(false);
  });

  it('should swap to the mobile statistics preview on a small screen', () => {
    isMdAndDown.current = true;

    wrapper = mountComponent();

    const sources = wrapper.findAllComponents(AppImageStub).map(item => item.props('src') ?? '');
    expect(sources.some(src => src.includes('liquity_staking_statistics_mobile.png'))).toBe(true);
  });
});
