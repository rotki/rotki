import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UnmatchedMatchDisabledAlert from '@/modules/history/events/UnmatchedMatchDisabledAlert.vue';

interface Props {
  variant: 'bridge' | 'asset-movement';
  premium?: boolean;
  currentTier?: string | null;
  matchMinimumTier?: string | null;
}

function mountAlert(props: Props): VueWrapper<InstanceType<typeof UnmatchedMatchDisabledAlert>> {
  return mount(UnmatchedMatchDisabledAlert, {
    props,
  });
}

describe('modules/history/events/UnmatchedMatchDisabledAlert', () => {
  it('should render the bridge premium message', () => {
    const wrapper = mountAlert({ premium: true, variant: 'bridge' });
    expect(wrapper.find('i18n-t-stub').attributes('keypath')).toBe('bridge_matching.premium.premium_tooltip');
  });

  it('should render the bridge free message', () => {
    const wrapper = mountAlert({ premium: false, variant: 'bridge' });
    expect(wrapper.find('i18n-t-stub').attributes('keypath')).toBe('bridge_matching.premium.free_tooltip');
  });

  it('should render the asset-movement premium message', () => {
    const wrapper = mountAlert({ premium: true, variant: 'asset-movement' });
    expect(wrapper.find('i18n-t-stub').attributes('keypath')).toBe('asset_movement_matching.premium.premium_tooltip');
  });

  it('should render the asset-movement free message', () => {
    const wrapper = mountAlert({ premium: false, variant: 'asset-movement' });
    expect(wrapper.find('i18n-t-stub').attributes('keypath')).toBe('asset_movement_matching.premium.free_tooltip');
  });
});
