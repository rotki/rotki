import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ActionCenterRow from '@/modules/core/action-center/ActionCenterRow.vue';
import { type ActionItem, ActionSeverity, type ActionTarget } from '@/modules/core/action-center/types';

function createItem(overrides: Partial<ActionItem> = {}): ActionItem {
  const target: ActionTarget = { kind: 'route', to: { name: '/balances/blockchain/' } };
  return {
    actionLabel: 'Match',
    checkTarget: target,
    count: 11,
    description: 'description',
    icon: 'lu-arrow-left-right',
    id: 'unmatched-movements',
    informational: false,
    loading: false,
    locked: false,
    minimumTier: null,
    severity: ActionSeverity.WARNING,
    target,
    title: 'Unmatched asset movements',
    ...overrides,
  };
}

// `VueWrapper` without type arguments: a generic SFC has no `InstanceType`.
function mountRow(item: ActionItem): VueWrapper {
  return mount(ActionCenterRow, { props: { item } });
}

describe('modules/core/action-center/ActionCenterRow', () => {
  it('should render the count, the description and the action', async () => {
    const item = createItem();
    const wrapper = mountRow(item);

    expect(wrapper.find('[data-testid=actions-center-row-count]').text()).toBe('11');
    expect(wrapper.text()).toContain('description');

    await wrapper.find('[data-testid=actions-center-row-action]').trigger('click');

    expect(wrapper.emitted('action')).toEqual([[item]]);
  });

  it('should replace the action with a premium gate when locked', () => {
    const wrapper = mountRow(createItem({ locked: true, minimumTier: 'Basic' }));

    expect(wrapper.find('[data-testid=actions-center-row-action]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=actions-center-row-locked]').text()).toContain('action_center.locked');
    // the tier hint replaces the description, which no longer describes anything actionable
    expect(wrapper.text()).toContain('action_center.locked_hint::Basic');
    expect(wrapper.text()).not.toContain('description');
  });

  it('should fall back to a generic hint when the tier is unknown', () => {
    const wrapper = mountRow(createItem({ locked: true }));

    expect(wrapper.text()).toContain('action_center.locked_hint_generic');
  });

  it('should keep a muted item out of the warning treatment', () => {
    const wrapper = mountRow(createItem({ id: 'internal-conflicts', severity: ActionSeverity.MUTED }));

    expect(wrapper.find('[data-testid=actions-center-row][data-key=unmatched-movements]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=actions-center-row][data-key=internal-conflicts]').classes()).not.toContain('opacity-60');
    expect(wrapper.find('.text-rui-warning').exists()).toBe(false);
  });
});
