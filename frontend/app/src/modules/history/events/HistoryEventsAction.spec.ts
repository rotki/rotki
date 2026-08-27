import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UseHistoryEventActionMenuOptions } from '@/modules/history/events/use-history-event-action-menu';
import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import HistoryEventsAction from '@/modules/history/events/HistoryEventsAction.vue';

const evmEvent = createMock<HistoryEventEntry>({
  entryType: HistoryEventEntryType.EVM_EVENT,
  identifier: 1,
  ignoredInAccounting: false,
  location: 'ethereum',
  txRef: '0xabc',
});

const blockEvent = createMock<HistoryEventEntry>({
  blockNumber: 1234,
  entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
  identifier: 2,
  ignoredInAccounting: false,
});

const redecodePayload = { data: { location: 'ethereum', txRef: '0xabc' }, type: HistoryEventEntryType.EVM_EVENT };

const menu = {
  blockEvent: ref<HistoryEventEntry | undefined>(),
  canAddEvent: ref<boolean>(true),
  canDeleteEvents: ref<boolean>(false),
  confirmFixDuplicate: vi.fn(),
  confirmIgnoreDuplicate: vi.fn(),
  decodableEvmEvent: ref<HistoryEventEntry | undefined>(evmEvent),
  deletableEventIds: vi.fn().mockReturnValue([7, 9]),
  ethBlockEventsDecoding: ref<boolean>(false),
  eventWithDecoding: ref<HistoryEventEntry | undefined>(evmEvent),
  eventWithTxRef: ref<{ location: string; txRef: string } | undefined>(),
  fixLoading: ref<boolean>(false),
  ignoreLoading: ref<boolean>(false),
  isAutoFixable: ref<boolean>(false),
  isDuplicate: ref<boolean>(false),
  openReportDialog: vi.fn(),
  toRedecodePayload: vi.fn().mockReturnValue(redecodePayload),
  txEventsDecoding: ref<boolean>(false),
};

let options: UseHistoryEventActionMenuOptions;

vi.mock('@/modules/history/events/use-history-event-action-menu', () => ({
  useHistoryEventActionMenu: (opts: UseHistoryEventActionMenuOptions): unknown => {
    options = opts;
    return menu;
  },
}));

const MenuStub = defineComponent({
  emits: ['update:modelValue'],
  name: 'RuiMenu',
  props: { modelValue: { default: false, type: Boolean } },
  setup: (_props, { slots }) => (): unknown => h('div', [slots.activator?.({ attrs: {} }), slots.default?.()]),
});

const RedecodeStub = defineComponent({
  emits: ['redecode', 'redecode-with-options'],
  name: 'RedecodeEventsButton',
  props: {
    disabled: { default: false, type: Boolean },
    hasOptions: { default: false, type: Boolean },
  },
  setup: () => (): unknown => h('div', { 'data-testid': 'redecode-button' }),
});

describe('modules/history/events/HistoryEventsAction', () => {
  let wrapper: VueWrapper | undefined;

  function mountAction(props: Record<string, unknown> = {}): VueWrapper {
    wrapper = mount(HistoryEventsAction, {
      global: {
        stubs: {
          RedecodeEventsButton: RedecodeStub,
          RuiMenu: MenuStub,
        },
      },
      props: { event: evmEvent, loading: false, ...props },
    });
    return wrapper;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(menu.blockEvent, undefined);
    set(menu.canAddEvent, true);
    set(menu.canDeleteEvents, false);
    set(menu.decodableEvmEvent, evmEvent);
    set(menu.ethBlockEventsDecoding, false);
    set(menu.eventWithDecoding, evmEvent);
    set(menu.eventWithTxRef, undefined);
    set(menu.fixLoading, false);
    set(menu.ignoreLoading, false);
    set(menu.isAutoFixable, false);
    set(menu.isDuplicate, false);
    set(menu.txEventsDecoding, false);
    menu.deletableEventIds.mockReturnValue([7, 9]);
    menu.toRedecodePayload.mockReturnValue(redecodePayload);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should hand the row and its group to the composable', () => {
    const group = [evmEvent];
    mountAction({ groupEvents: group });

    expect(options.event()).toBe(evmEvent);
    expect(options.groupEvents()).toStrictEqual(group);
    expect(options.duplicateHandlingStatus()).toBeUndefined();
  });

  describe('the duplicate actions', () => {
    it('should show neither while the row is not a duplicate', () => {
      const view = mountAction();

      expect(view.find('[data-testid="event-fix-duplicate"]').exists()).toBe(false);
      expect(view.find('[data-testid="event-ignore-duplicate"]').exists()).toBe(false);
    });

    it('should fix the duplicate through the composable', async () => {
      set(menu.isAutoFixable, true);
      const view = mountAction();

      await view.find('[data-testid="event-fix-duplicate"]').trigger('click');

      expect(menu.confirmFixDuplicate).toHaveBeenCalledTimes(1);
    });

    it('should dismiss the duplicate through the composable', async () => {
      set(menu.isDuplicate, true);
      const view = mountAction();

      await view.find('[data-testid="event-ignore-duplicate"]').trigger('click');

      expect(menu.confirmIgnoreDuplicate).toHaveBeenCalledTimes(1);
    });

    it('should report each action back once it is done', () => {
      const view = mountAction();

      options.onFixDuplicate();
      options.onIgnoreDuplicate();

      expect(view.emitted('fix-duplicate')).toHaveLength(1);
      expect(view.emitted('ignore-duplicate')).toHaveLength(1);
    });
  });

  describe('the menu items', () => {
    it('should add an event next to the row', async () => {
      const view = mountAction();

      await view.find('[data-testid="event-add"]').trigger('click');

      expect(view.emitted('add-event')).toStrictEqual([[evmEvent]]);
    });

    it('should hide the add action when the composable refuses it', () => {
      set(menu.canAddEvent, false);
      const view = mountAction();

      expect(view.find('[data-testid="event-add"]').exists()).toBe(false);
    });

    it('should toggle the row out of accounting', async () => {
      const view = mountAction();

      const toggle = view.find('[data-testid="event-toggle-ignore"]');
      // The icon name is part of the rendered text, which is what shows the eye is crossed out.
      expect(toggle.text()).toBe('lu-eye-off transactions.ignore');
      await toggle.trigger('click');

      expect(view.emitted('toggle-ignore')).toStrictEqual([[evmEvent]]);
    });

    it('should offer to bring an ignored row back', () => {
      const ignored = createMock<HistoryEventEntry>({
        entryType: HistoryEventEntryType.EVM_EVENT,
        identifier: 1,
        ignoredInAccounting: true,
      });
      const view = mountAction({ event: ignored });

      expect(view.find('[data-testid="event-toggle-ignore"]').text()).toBe('lu-eye transactions.unignore');
    });

    it('should report an issue about the row', async () => {
      const view = mountAction();

      await view.find('[data-testid="event-report-issue"]').trigger('click');

      expect(menu.openReportDialog).toHaveBeenCalledTimes(1);
    });
  });

  describe('re-decoding', () => {
    it('should re-decode a block event by its own action', async () => {
      set(menu.blockEvent, blockEvent);
      const blockPayload = { data: [1234], type: HistoryEventEntryType.ETH_BLOCK_EVENT };
      menu.toRedecodePayload.mockReturnValue(blockPayload);
      const view = mountAction();

      expect(view.findComponent(RedecodeStub).exists()).toBe(false);
      await view.find('[data-testid="event-redecode-block"]').trigger('click');

      expect(menu.toRedecodePayload).toHaveBeenCalledWith(blockEvent);
      expect(view.emitted('redecode')).toStrictEqual([[blockPayload]]);
    });

    it.each([
      ['the table is loading', { loading: true }],
      ['this group is already re-decoding', { redecoding: true }],
    ] as const)('should disable the block re-decode while %s', (_, props) => {
      set(menu.blockEvent, blockEvent);
      const view = mountAction(props);

      expect(view.find('[data-testid="event-redecode-block"]').attributes('disabled')).toBeDefined();
    });

    it('should disable the block re-decode while every block event is decoding', () => {
      set(menu.blockEvent, blockEvent);
      set(menu.ethBlockEventsDecoding, true);
      const view = mountAction();

      expect(view.find('[data-testid="event-redecode-block"]').attributes('disabled')).toBeDefined();
    });

    it('should re-decode everything else through the redecode button', async () => {
      const view = mountAction();
      const button = view.findComponent(RedecodeStub);

      expect(button.props('hasOptions')).toBe(true);
      expect(button.props('disabled')).toBe(false);
      button.vm.$emit('redecode');
      await nextTick();

      expect(menu.toRedecodePayload).toHaveBeenCalledWith(evmEvent);
      expect(view.emitted('redecode')).toStrictEqual([[redecodePayload]]);
    });

    it('should offer no options when the event a re-decode runs on is not an evm one', () => {
      set(menu.decodableEvmEvent, undefined);
      const view = mountAction();

      expect(view.findComponent(RedecodeStub).props('hasOptions')).toBe(false);
    });

    it('should disable the redecode button while transactions are decoding', () => {
      set(menu.txEventsDecoding, true);
      const view = mountAction();

      expect(view.findComponent(RedecodeStub).props('disabled')).toBe(true);
    });

    it('should re-decode with options and close the menu', async () => {
      const view = mountAction();
      expect(view.findComponent(MenuStub).props('modelValue')).toBe(false);

      view.findComponent(MenuStub).vm.$emit('update:modelValue', true);
      await nextTick();
      expect(view.findComponent(MenuStub).props('modelValue')).toBe(true);

      view.findComponent(RedecodeStub).vm.$emit('redecode-with-options');
      await nextTick();

      expect(view.emitted('redecode-with-options')).toStrictEqual([[redecodePayload]]);
      expect(view.findComponent(MenuStub).props('modelValue')).toBe(false);
    });

    it('should render nothing to re-decode when the composable found no event for it', () => {
      set(menu.eventWithDecoding, undefined);
      const view = mountAction();

      expect(view.findComponent(RedecodeStub).exists()).toBe(false);
      expect(view.find('[data-testid="event-redecode-block"]').exists()).toBe(false);
    });
  });

  describe('deleting', () => {
    it('should delete the transaction when the row belongs to one', async () => {
      set(menu.eventWithTxRef, { location: 'ethereum', txRef: '0xabc' });
      const view = mountAction();

      expect(view.find('[data-testid="event-delete-events"]').exists()).toBe(false);
      await view.find('[data-testid="event-delete-tx"]').trigger('click');

      expect(view.emitted('delete-tx')).toStrictEqual([[{ location: 'ethereum', txRef: '0xabc' }]]);
    });

    it('should delete every event the composable names when there is no transaction', async () => {
      set(menu.canDeleteEvents, true);
      const view = mountAction();

      expect(view.find('[data-testid="event-delete-tx"]').exists()).toBe(false);
      await view.find('[data-testid="event-delete-events"]').trigger('click');

      expect(view.emitted('delete-events')).toStrictEqual([[[7, 9]]]);
    });

    it('should offer no delete when neither applies', () => {
      const view = mountAction();

      expect(view.find('[data-testid="event-delete-tx"]').exists()).toBe(false);
      expect(view.find('[data-testid="event-delete-events"]').exists()).toBe(false);
    });

    it('should disable the delete while the table is loading', () => {
      set(menu.canDeleteEvents, true);
      const view = mountAction({ loading: true });

      expect(view.find('[data-testid="event-delete-events"]').attributes('disabled')).toBeDefined();
    });
  });
});
