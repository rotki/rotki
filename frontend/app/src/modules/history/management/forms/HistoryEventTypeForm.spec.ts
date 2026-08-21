import type { HistoryEventCategoryDetailWithId } from '@/modules/history/events/event-type';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';

const push = vi.fn(async (): Promise<void> => {});
const show = vi.fn<(options: unknown, onConfirm: () => void) => void>();
const findEventTypeData = vi.fn<() => HistoryEventCategoryDetailWithId>();

vi.mock('vue-router', () => ({
  useRouter: (): { push: typeof push } => ({ push }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { show: typeof show } => ({ show }),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): unknown => ({ findEventTypeData }),
}));

function categoryDetail(identifier: string): HistoryEventCategoryDetailWithId {
  return { direction: 'in', icon: 'lu-download', identifier, label: 'Claim reward' };
}

describe('forms/HistoryEventTypeForm.vue', () => {
  const wrappers: VueWrapper[] = [];

  beforeEach(() => {
    push.mockClear();
    show.mockClear();
    findEventTypeData.mockReturnValue(categoryDetail('claim reward'));
  });

  afterEach(() => {
    while (wrappers.length > 0) wrappers.pop()?.unmount();
  });

  function mountForm(props: Record<string, unknown>): VueWrapper {
    const wrapper = mount(HistoryEventTypeForm, {
      global: {
        stubs: { HistoryEventActionPicker: true },
      },
      props: {
        eventSubtype: 'reward',
        eventType: 'staking',
        errorMessages: { eventSubtype: [], eventType: [] },
        ...props,
      },
    });
    wrappers.push(wrapper);
    return wrapper;
  }

  it('should not warn when the combination resolves for an empty counterparty', () => {
    const wrapper = mountForm({ counterparty: '' });

    expect(findEventTypeData).toHaveBeenCalledWith(
      { counterparty: '', eventSubtype: 'reward', eventType: 'staking', location: null },
      false,
    );
    expect(wrapper.find('[data-testid="alert"]').exists()).toBe(false);
  });

  it('should warn when the combination resolves to no identifier', () => {
    findEventTypeData.mockReturnValue(categoryDetail(''));

    const wrapper = mountForm({});

    expect(wrapper.find('[data-testid="alert"]').attributes('data-type')).toBe('warning');
  });

  it('should not warn until both the type and the subtype are set', () => {
    findEventTypeData.mockReturnValue(categoryDetail(''));

    const wrapper = mountForm({ eventSubtype: '' });

    expect(wrapper.find('[data-testid="alert"]').exists()).toBe(false);
  });

  it('should not warn when the parent disables the warning', () => {
    findEventTypeData.mockReturnValue(categoryDetail(''));

    const wrapper = mountForm({ disableWarning: true });

    expect(wrapper.find('[data-testid="alert"]').exists()).toBe(false);
  });

  it('should not render the accounting rule link by default', () => {
    const wrapper = mountForm({});
    expect(wrapper.find('[data-testid="view-accounting-rule"]').exists()).toBe(false);
  });

  it('should navigate to the filtered accounting rules screen with counterparty', async () => {
    const wrapper = mountForm({ counterparty: 'aave-v3', showAccountingRuleLink: true });

    await wrapper.find('[data-testid="view-accounting-rule"]').trigger('click');

    expect(push).toHaveBeenCalledWith({
      name: '/settings/accounting/',
      query: { counterparties: 'aave-v3', eventSubtypes: 'reward', eventTypes: 'staking' },
    });
  });

  it('should omit the counterparty filter when none is set', async () => {
    const wrapper = mountForm({ showAccountingRuleLink: true });

    await wrapper.find('[data-testid="view-accounting-rule"]').trigger('click');

    expect(push).toHaveBeenCalledWith({
      name: '/settings/accounting/',
      query: { eventSubtypes: 'reward', eventTypes: 'staking' },
    });
  });

  it('should not render the link when the type or subtype is empty', () => {
    const wrapper = mountForm({ eventSubtype: '', showAccountingRuleLink: true });
    expect(wrapper.find('[data-testid="view-accounting-rule"]').exists()).toBe(false);
  });

  it('should confirm before navigating when the form has unsaved changes', async () => {
    const wrapper = mountForm({ dirty: true, showAccountingRuleLink: true });

    await wrapper.find('[data-testid="view-accounting-rule"]').trigger('click');

    expect(push).not.toHaveBeenCalled();
    expect(show).toHaveBeenCalledTimes(1);

    // invoking the confirm callback performs the navigation
    const onConfirm = show.mock.calls[0][1];
    onConfirm();
    expect(push).toHaveBeenCalledWith({
      name: '/settings/accounting/',
      query: { eventSubtypes: 'reward', eventTypes: 'staking' },
    });
  });
});
