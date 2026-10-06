import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';

const { currentTier, premium } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { currentTier: ref<string>('Free'), premium: ref<boolean>(false) };
});

vi.mock('@/modules/premium/use-premium', () => ({ usePremium: (): typeof premium => premium }));
vi.mock('@/modules/premium/use-premium-helper', () => ({
  usePremiumHelper: (): Record<string, unknown> => ({ currentTier }),
}));

interface Props {
  variant: 'bridge' | 'asset-movement';
  count?: number;
  matchMinimumTier?: string | null;
}

const I18nTStub = {
  props: ['keypath', 'plural'],
  template: `<div class="message" :data-keypath="keypath" :data-plural="plural">
    <span class="count"><slot name="count" /></span>
    <span class="tier"><slot name="tier" /></span>
    <span class="current-tier"><slot name="currentTier" /></span>
  </div>`,
};

function mountAlert(props: Props): VueWrapper<InstanceType<typeof UnmatchedMatchDisabledAlert>> {
  return mount(UnmatchedMatchDisabledAlert, {
    props,
    global: { stubs: { ExternalLink: true, I18nT: I18nTStub } },
  });
}

describe('modules/history/events/UnmatchedMatchDisabledAlert', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(currentTier, 'Free');
  });

  it('should state the unmatched bridge transactions when there are some', () => {
    const wrapper = mountAlert({ count: 17, matchMinimumTier: 'Basic', variant: 'bridge' });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('bridge_matching.premium.unmatched');
    expect(wrapper.find('.message').attributes('data-plural')).toBe('17');
    expect(wrapper.find('.count').text()).toBe('17');
  });

  it('should fall back to the bridge message without a count', () => {
    const wrapper = mountAlert({ matchMinimumTier: 'Basic', variant: 'bridge' });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('bridge_matching.premium.locked');
  });

  it('should state the unmatched asset movements when there are some', () => {
    const wrapper = mountAlert({ count: 3, matchMinimumTier: 'Basic', variant: 'asset-movement' });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('asset_movement_matching.premium.unmatched');
  });

  it('should fall back to the asset movement message without a count', () => {
    const wrapper = mountAlert({ matchMinimumTier: 'Basic', variant: 'asset-movement' });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('asset_movement_matching.premium.locked');
  });

  it('should name the unlocking plan and the current plan', () => {
    set(currentTier, 'Lite');
    const wrapper = mountAlert({ count: 1, matchMinimumTier: 'Basic', variant: 'bridge' });
    expect(wrapper.find('.tier').text()).toBe('Basic');
    expect(wrapper.find('.current-tier').text()).toBe('Lite');
  });

  it('should name the product when the server did not say which plan unlocks matching', () => {
    const wrapper = mountAlert({ count: 1, variant: 'bridge' });
    expect(wrapper.find('.tier').text()).toBe('premium_settings.title');
  });
});
