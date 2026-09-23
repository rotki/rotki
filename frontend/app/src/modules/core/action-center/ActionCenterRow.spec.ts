import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ActionCenterRow from '@/modules/core/action-center/ActionCenterRow.vue';
import { type ActionItem, type ActionTarget, ActionUrgency } from '@/modules/core/action-center/types';

function createItem(overrides: Partial<ActionItem> = {}): ActionItem {
  const target: ActionTarget = { kind: 'route', to: { name: '/balances/blockchain/' } };
  return {
    actionLabel: 'Match',
    checkTarget: target,
    choices: [],
    count: 11,
    description: 'description',
    icon: 'lu-arrow-left-right',
    id: 'unmatched-movements',
    informational: false,
    loading: false,
    locked: false,
    minimumTier: null,
    options: [],
    urgency: ActionUrgency.DECISION,
    target,
    title: 'Unmatched asset movements',
    ...overrides,
  };
}

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

  it('should drop the urgency colour from a row the user set aside, keeping its action', async () => {
    const wrapper = mountRow(createItem());
    expect(wrapper.findComponent({ name: 'RuiChip' }).props('color')).toBe('warning');

    await wrapper.setProps({ item: createItem({ informational: true }) });

    expect(wrapper.findComponent({ name: 'RuiChip' }).props('color')).not.toBe('warning');
    expect(wrapper.find('[data-testid=actions-center-row-action]').exists()).toBe(true);
  });

  it('should mark a row as new only when told it is', async () => {
    const wrapper = mountRow(createItem());
    expect(wrapper.find('[data-testid=actions-center-row-new]').exists()).toBe(false);

    await wrapper.setProps({ isNew: true });

    expect(wrapper.find('[data-testid=actions-center-row-new]').text()).toBe('action_center.new');
  });

  it('should turn the action into a menu of choices, handing the chosen one\'s target up instead of the action', async () => {
    const exchange: ActionTarget = { kind: 'route', to: { name: '/api-keys/exchanges/' } };
    const bank: ActionTarget = { kind: 'route', to: { name: '/api-keys/banks/' } };
    const wrapper = mount(ActionCenterRow, {
      global: { stubs: { RuiMenu: { template: '<div><slot name="activator" :attrs="{}" /><slot /></div>' } } },
      props: {
        item: createItem({
          choices: [
            { icon: 'lu-building-2', id: 'add-exchange', label: 'Exchange', target: exchange },
            { icon: 'lu-landmark', id: 'add-bank', label: 'Bank', target: bank },
          ],
        }),
      },
    });

    const choices = wrapper.findAll('[data-testid=actions-center-row-choice]');
    expect(choices.map(choice => choice.attributes('data-key'))).toEqual(['add-exchange', 'add-bank']);

    await wrapper.find('[data-testid=actions-center-row-action]').trigger('click');
    await choices[1].trigger('click');

    expect(wrapper.emitted('action')).toBeUndefined();
    expect(wrapper.emitted('option')).toEqual([[bank]]);
  });

  it('should list no options for a row that has none', () => {
    expect(mountRow(createItem()).find('[data-testid=actions-center-row-option]').exists()).toBe(false);
  });

  it('should list the options in order and hand the chosen one\'s target up, not the main action', async () => {
    const guide: ActionTarget = { kind: 'external', url: 'https://docs.rotki.com' };
    const wrapper = mountRow(createItem({
      options: [
        { icon: 'lu-book-open', id: 'guide', label: 'Guide', target: guide },
        { danger: true, icon: 'lu-bell-off', id: 'do-not-show-again', label: 'Silence', target: { kind: 'run', run: vi.fn() } },
      ],
    }));

    const options = wrapper.findAll('[data-testid=actions-center-row-option]');
    expect(options.map(option => option.attributes('data-key'))).toEqual(['guide', 'do-not-show-again']);

    await options[0].trigger('click');

    expect(wrapper.emitted('option')).toEqual([[guide]]);
    expect(wrapper.emitted('action')).toBeUndefined();
  });

  it('should hide the options of a locked row along with its action', () => {
    const wrapper = mountRow(createItem({
      locked: true,
      options: [{ icon: 'lu-book-open', id: 'guide', label: 'Guide', target: { kind: 'external', url: 'https://docs.rotki.com' } }],
    }));

    expect(wrapper.find('[data-testid=actions-center-row-option]').exists()).toBe(false);
  });

  it('should replace the action with a premium gate when locked', () => {
    const wrapper = mountRow(createItem({ locked: true, minimumTier: 'Basic' }));

    expect(wrapper.find('[data-testid=actions-center-row-action]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=actions-center-row-locked]').text()).toContain('action_center.locked');
    expect(wrapper.text()).toContain('action_center.locked_hint::Basic');
    expect(wrapper.text()).not.toContain('description');
  });

  it('should fall back to a generic hint when the tier is unknown', () => {
    const wrapper = mountRow(createItem({ locked: true }));

    expect(wrapper.text()).toContain('action_center.locked_hint_generic');
  });

  it('should keep a muted item out of the warning treatment', () => {
    const wrapper = mountRow(createItem({ id: 'internal-conflicts', urgency: ActionUrgency.AUTOMATIC }));

    expect(wrapper.find('[data-testid=actions-center-row][data-key=unmatched-movements]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=actions-center-row][data-key=internal-conflicts]').classes()).not.toContain('opacity-60');
    expect(wrapper.find('.text-rui-warning').exists()).toBe(false);
  });
});
