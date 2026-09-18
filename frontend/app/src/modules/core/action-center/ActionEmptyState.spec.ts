import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ActionEmptyState from '@/modules/core/action-center/ActionEmptyState.vue';
import { type ActionItem, type ActionItemDefinition, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';

const { push } = vi.hoisted(() => ({
  push: vi.fn<(to: unknown) => Promise<void>>(),
}));

vi.mock('vue-router', () => ({
  useRouter: (): object => ({ push }),
}));

function item(overrides: Partial<ActionItemDefinition<ActionTarget, string>> = {}): ActionItem {
  return createActionItem<ActionTarget, string>({
    actionLabel: 'Add a source',
    count: 1,
    description: 'Nothing is tracked',
    icon: 'lu-wallet',
    id: 'no-tracked-accounts',
    target: { kind: 'route', to: { name: '/accounts/' } },
    title: 'Tracked accounts',
    urgency: ActionUrgency.DECISION,
    ...overrides,
  });
}

function mountState(value: ActionItem): VueWrapper {
  return mount(ActionEmptyState, {
    global: { stubs: { RuiMenu: { template: '<div><slot name="activator" :attrs="{}" /><slot /></div>' } } },
    props: { item: value },
  });
}

describe('modules/core/action-center/ActionEmptyState', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    push.mockReset().mockResolvedValue();
  });

  it('should show the row\'s description and action, without the title and count of a center row', () => {
    const wrapper = mountState(item());

    expect(wrapper.text()).toContain('Nothing is tracked');
    expect(wrapper.find('[data-testid=actions-center-row-action]').text()).toContain('Add a source');
    expect(wrapper.text()).not.toContain('Tracked accounts');
    expect(wrapper.find('[data-testid=actions-center-row-count]').exists()).toBe(false);
  });

  it('should follow the row action from the page, outside the center', async () => {
    const wrapper = mountState(item());

    await wrapper.find('[data-testid=actions-center-row-action]').trigger('click');

    expect(push).toHaveBeenCalledExactlyOnceWith({ name: '/accounts/' });
  });

  it('should follow the chosen one when the action offers choices', async () => {
    const bank: ActionTarget = { kind: 'route', to: { name: '/api-keys/banks/' } };
    const wrapper = mountState(item({
      choices: [{ icon: 'lu-landmark', id: 'add-bank', label: 'Bank', target: bank }],
    }));

    await wrapper.find('[data-testid=actions-center-row-choice]').trigger('click');

    expect(push).toHaveBeenCalledExactlyOnceWith({ name: '/api-keys/banks/' });
  });
});
