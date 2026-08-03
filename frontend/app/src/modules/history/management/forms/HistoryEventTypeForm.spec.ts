import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';

const push = vi.fn(async (): Promise<void> => {});
const show = vi.fn<(options: unknown, onConfirm: () => void) => void>();

vi.mock('vue-router', () => ({
  useRouter: (): { push: typeof push } => ({ push }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { show: typeof show } => ({ show }),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): unknown => ({
    findEventTypeData: (): { value: { identifier: string } } => ({ value: { identifier: 'receive' } }),
  }),
}));

describe('forms/HistoryEventTypeForm.vue', () => {
  beforeEach(() => {
    push.mockClear();
    show.mockClear();
  });

  function mountForm(props: Record<string, unknown>): VueWrapper {
    return mount(HistoryEventTypeForm, {
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
  }

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
