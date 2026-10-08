import { resetOverlayStack, useOverlayStack } from '@rotki/ui-library';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import ActionCenterMenu from '@/modules/core/action-center/ActionCenterMenu.vue';
import { ActionUrgency } from '@/modules/core/action-center/types';

interface MenuProps {
  count: number;
  urgency?: ActionUrgency;
  newCount?: number;
  checking?: boolean;
  badge?: boolean;
}

/** Pending categories always carry an urgency, so a count without one stands for a decision. */
function mountMenu(props: MenuProps): VueWrapper<InstanceType<typeof ActionCenterMenu>> {
  const urgency = props.urgency ?? (props.count > 0 ? ActionUrgency.DECISION : undefined);
  return mount(ActionCenterMenu, { props: { ...props, urgency }, slots: { default: '<div>panel</div>' } });
}

describe('modules/core/action-center/ActionCenterMenu', () => {
  it('should show only the new categories as the number on the badge', () => {
    const wrapper = mountMenu({ badge: true, count: 3, newCount: 1 });
    const badge = wrapper.findComponent({ name: 'RuiBadge' });

    expect(badge.props('modelValue')).toBe(true);
    expect(badge.props('dot')).toBe(false);
    expect(badge.props('text')).toBe('1');
  });

  it('should show an empty dot when categories are pending but none of them is new', () => {
    const wrapper = mountMenu({ badge: true, count: 3, newCount: 0 });
    const badge = wrapper.findComponent({ name: 'RuiBadge' });

    expect(badge.props('modelValue')).toBe(true);
    expect(badge.props('dot')).toBe(true);
    expect(badge.props('text')).toBeNull();
  });

  it('should keep the count off a trigger that does not carry the badge', () => {
    const wrapper = mountMenu({ count: 3 });

    expect(wrapper.findComponent({ name: 'RuiBadge' }).props('modelValue')).toBe(false);
  });

  it('should hide the badge when nothing asks for anything', () => {
    const wrapper = mountMenu({ badge: true, count: 0 });

    expect(wrapper.findComponent({ name: 'RuiBadge' }).props('modelValue')).toBe(false);
  });

  it.each([
    [ActionUrgency.DECISION, 'lu-triangle-alert', 'warning'],
    [ActionUrgency.TODO, 'lu-list-todo', 'info'],
    [ActionUrgency.AUTOMATIC, 'lu-list-todo', 'secondary'],
  ])('should take its icon and badge colour from the most pressing urgency (%s)', (urgency, icon, color) => {
    const wrapper = mountMenu({ badge: true, count: 1, urgency });

    expect(wrapper.find('[data-testid=actions-center-button] .rui-icon').text()).toBe(icon);
    expect(wrapper.findComponent({ name: 'RuiBadge' }).props('color')).toBe(color);
  });

  it('should spell the count out in the accessible name, since a badge reaches a screen reader as a bare number', () => {
    const wrapper = mountMenu({ badge: true, count: 3 });

    expect(wrapper.find('[data-testid=actions-center-button]').attributes('aria-label')).toBe('action_center.subtitle::3');
  });

  it('should add how many are new to the accessible name', () => {
    const wrapper = mountMenu({ badge: true, count: 3, newCount: 2 });

    expect(wrapper.find('[data-testid=actions-center-button]').attributes('aria-label'))
      .toBe('action_center.subtitle::3, action_center.new_count::2');
  });

  it.each([
    [true, 'action_center.button_checking'],
    [false, 'action_center.button_clear'],
  ])('should name the empty state apart from the pending one (checking: %s)', (checking, label) => {
    const wrapper = mountMenu({ checking, count: 0 });

    expect(wrapper.find('[data-testid=actions-center-button]').attributes('aria-label')).toBe(label);
  });

  describe('dismissed from the overlay stack, as the back gesture does', () => {
    beforeEach(() => {
      resetOverlayStack();
    });

    it('should close the open menu', () => {
      const wrapper = mount(ActionCenterMenu, {
        props: { 'count': 1, 'modelValue': true, 'onUpdate:modelValue': async (value: boolean) => wrapper.setProps({ modelValue: value }), 'urgency': ActionUrgency.DECISION },
        slots: { default: '<div>panel</div>' },
      });

      expect(useOverlayStack().dismissTop()).toBe(true);
      expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
    });

    it('should leave nothing to dismiss while the menu is closed', () => {
      mountMenu({ count: 1 });

      expect(useOverlayStack().dismissTop()).toBe(false);
    });
  });
});
