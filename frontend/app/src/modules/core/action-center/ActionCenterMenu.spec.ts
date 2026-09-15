import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ActionCenterMenu from '@/modules/core/action-center/ActionCenterMenu.vue';

interface MenuProps {
  count: number;
  checking?: boolean;
  badge?: boolean;
}

function mountMenu(props: MenuProps): VueWrapper<InstanceType<typeof ActionCenterMenu>> {
  return mount(ActionCenterMenu, { props, slots: { default: '<div>panel</div>' } });
}

describe('modules/core/action-center/ActionCenterMenu', () => {
  it('should show the count on the trigger when it carries the badge', () => {
    const wrapper = mountMenu({ badge: true, count: 3 });
    const badge = wrapper.findComponent({ name: 'RuiBadge' });

    expect(badge.props('modelValue')).toBe(true);
    expect(badge.props('text')).toBe('3');
  });

  it('should keep the count off a trigger that does not carry the badge', () => {
    const wrapper = mountMenu({ count: 3 });

    expect(wrapper.findComponent({ name: 'RuiBadge' }).props('modelValue')).toBe(false);
  });

  it('should hide the badge when nothing asks for anything', () => {
    const wrapper = mountMenu({ badge: true, count: 0 });

    expect(wrapper.findComponent({ name: 'RuiBadge' }).props('modelValue')).toBe(false);
  });

  it('should spell the count out in the accessible name, since a badge reaches a screen reader as a bare number', () => {
    const wrapper = mountMenu({ badge: true, count: 3 });

    expect(wrapper.find('[data-testid=actions-center-button]').attributes('aria-label')).toBe('action_center.subtitle::3');
  });

  it.each([
    [true, 'action_center.button_checking'],
    [false, 'action_center.button_clear'],
  ])('should name the empty state apart from the pending one (checking: %s)', (checking, label) => {
    const wrapper = mountMenu({ checking, count: 0 });

    expect(wrapper.find('[data-testid=actions-center-button]').attributes('aria-label')).toBe(label);
  });
});
