import type { DialogState } from '@/modules/history/events/dialog-manager/types';
import type { UseHistoryEventsDialogContainerOptions } from '@/modules/history/events/use-history-events-dialog-container';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as stubs from '@/modules/history/events/dialog-components';
import { DIALOG_TYPES, type DialogEventHandlers } from '@/modules/history/events/dialog-types';
import HistoryEventsDialogContainer from '@/modules/history/events/HistoryEventsDialogContainer.vue';

/**
 * The seam: which dialog the container renders for the open dialog type, and where each
 * dialog's events go. The models behind them live in `use-history-events-dialog-container`,
 * which has its own spec.
 */

// Every dialog is replaced by a stub that renders nothing, so the container's own wiring is
// what the assertions see. `stubs` below is the mocked module itself, so a `findComponent`
// is matching the exact component the container rendered.
vi.mock('@/modules/history/events/dialog-components', async () => {
  const { defineComponent, h } = await import('vue');

  function stubDialog(name: string, emits: string[] = []): unknown {
    return defineComponent({
      emits: ['update:modelValue', ...emits],
      name,
      props: { modelValue: { default: undefined, type: [Boolean, Object] } },
      setup: () => (): unknown => h('div', { 'data-testid': name }),
    });
  }

  return {
    AccountingRuleFormDialog: stubDialog('AccountingRuleFormDialog', ['refresh']),
    BridgePotentialMatchesDialog: stubDialog('BridgePotentialMatchesDialog', ['matched', 'pinned']),
    CustomizedEventDuplicatesDialog: stubDialog('CustomizedEventDuplicatesDialog'),
    HistoryEventFormDialog: stubDialog('HistoryEventFormDialog', ['refresh']),
    HistoryEventsDecodingStatusDialog: stubDialog('HistoryEventsDecodingStatusDialog', [
      'redecode-all-events',
      'reset-undecoded-transactions',
    ]),
    HistoryEventsProtocolCacheStatusDialog: stubDialog('HistoryEventsProtocolCacheStatusDialog'),
    InternalTxConflictsDialog: stubDialog('InternalTxConflictsDialog'),
    MatchAssetMovementsDialog: stubDialog('MatchAssetMovementsDialog', ['find-match', 'refresh']),
    MatchBridgeTransactionsDialog: stubDialog('MatchBridgeTransactionsDialog', ['find-match']),
    MissingRulesDialog: stubDialog('MissingRulesDialog', ['add', 'dismiss', 'edit-event', 'redecode']),
    PotentialMatchesDialog: stubDialog('PotentialMatchesDialog', ['matched', 'pinned']),
    RepullingTransactionFormDialog: stubDialog('RepullingTransactionFormDialog'),
    TransactionFormDialog: stubDialog('TransactionFormDialog', ['reload']),
  };
});

const movement = createMock<UnmatchedAssetMovement>({ groupIdentifier: 'group-a' });
const transaction = createMock<UnmatchedBridgeTransaction>({ groupIdentifier: 'group-b' });

const container = {
  bridgeSubject: ref<UnmatchedBridgeTransaction | undefined>(),
  closeDialog: vi.fn(),
  currentDialog: ref<DialogState>({ type: 'closed' }),
  decodingStatusPersistent: ref<boolean>(false),
  modelAddTransaction: ref<unknown>(),
  modelBridgeMatchesOpen: ref<boolean>(false),
  modelDialogOpen: ref<boolean>(true),
  modelFormData: ref<unknown>(),
  modelMissingRule: ref<unknown>(),
  modelMovementMatchesOpen: ref<boolean>(false),
  movementSubject: ref<UnmatchedAssetMovement | undefined>(),
  onBridgeMatched: vi.fn(),
  onBridgePinned: vi.fn(),
  onMovementMatched: vi.fn(),
  onMovementPinned: vi.fn(),
  openBridgeMatches: vi.fn(),
  openMovementMatches: vi.fn(),
  show: vi.fn().mockResolvedValue(undefined),
};

let options: UseHistoryEventsDialogContainerOptions;

vi.mock('@/modules/history/events/use-history-events-dialog-container', () => ({
  useHistoryEventsDialogContainer: (opts: UseHistoryEventsDialogContainerOptions): unknown => {
    options = opts;
    return container;
  },
}));

describe('modules/history/events/HistoryEventsDialogContainer', () => {
  type ContainerWrapper = VueWrapper<InstanceType<typeof HistoryEventsDialogContainer>>;

  let wrapper: ContainerWrapper | undefined;

  const eventHandlers: DialogEventHandlers = {
    onHistoryEventSaved: vi.fn(),
    onRedecodeAllEvents: vi.fn(),
    onRedecodeTransaction: vi.fn(),
    onResetUndecodedTransactions: vi.fn(),
    onTransactionAdded: vi.fn(),
  };

  function mountContainer(props: Record<string, unknown> = {}): ContainerWrapper {
    wrapper = mount(HistoryEventsDialogContainer, {
      props: {
        accountingRuleToEdit: undefined,
        eventHandlers,
        selectedEventIds: [1, 2],
        ...props,
      },
    });
    return wrapper;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(container.bridgeSubject, undefined);
    set(container.currentDialog, { type: 'closed' });
    set(container.decodingStatusPersistent, false);
    set(container.modelBridgeMatchesOpen, false);
    set(container.modelDialogOpen, true);
    set(container.modelMovementMatchesOpen, false);
    set(container.movementSubject, undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should render only the accounting rule form while no dialog is open', () => {
    const view = mountContainer();

    // It is the one dialog with no `v-if`: it decides for itself from its own model.
    expect(view.findComponent(stubs.AccountingRuleFormDialog).exists()).toBe(true);
    expect(view.findComponent(stubs.HistoryEventFormDialog).exists()).toBe(false);
    expect(view.findComponent(stubs.TransactionFormDialog).exists()).toBe(false);
    expect(view.findComponent(stubs.MissingRulesDialog).exists()).toBe(false);
  });

  it.each([
    [DIALOG_TYPES.EVENT_FORM, 'HistoryEventFormDialog'],
    [DIALOG_TYPES.TRANSACTION_FORM, 'TransactionFormDialog'],
    [DIALOG_TYPES.REPULLING_TRANSACTION, 'RepullingTransactionFormDialog'],
    [DIALOG_TYPES.MISSING_RULES, 'MissingRulesDialog'],
    [DIALOG_TYPES.DECODING_STATUS, 'HistoryEventsDecodingStatusDialog'],
    [DIALOG_TYPES.PROTOCOL_CACHE, 'HistoryEventsProtocolCacheStatusDialog'],
    [DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES, 'CustomizedEventDuplicatesDialog'],
    [DIALOG_TYPES.INTERNAL_TX_CONFLICTS, 'InternalTxConflictsDialog'],
    [DIALOG_TYPES.MATCH_ASSET_MOVEMENTS, 'MatchAssetMovementsDialog'],
    [DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS, 'MatchBridgeTransactionsDialog'],
  ] as const)('should render the %s dialog and nothing else', (type, expected) => {
    set(container.currentDialog, createMock<DialogState>({ type }));
    const view = mountContainer();

    const rendered = Object.entries(stubs)
      .filter(([, stub]) => view.findComponent(stub).exists())
      .map(([name]) => name);

    expect(rendered).toStrictEqual(expect.arrayContaining([expected]));
    expect(rendered).toHaveLength(2); // the dialog itself, plus the accounting rule form
  });

  it('should give the decoding status dialog what the composable decided about persistence', () => {
    set(container.currentDialog, createMock<DialogState>({ type: DIALOG_TYPES.DECODING_STATUS }));
    set(container.decodingStatusPersistent, true);
    const view = mountContainer({ refreshing: true });

    const dialog = view.findComponent(stubs.HistoryEventsDecodingStatusDialog);
    expect(dialog.attributes('persistent')).toBeDefined();
    expect(dialog.attributes('refreshing')).toBeDefined();
  });

  describe('where each dialog reports to', () => {
    it('should reload the events when one is saved', async () => {
      set(container.currentDialog, createMock<DialogState>({ type: DIALOG_TYPES.EVENT_FORM }));
      const view = mountContainer();

      view.findComponent(stubs.HistoryEventFormDialog).vm.$emit('refresh');
      await nextTick();

      expect(eventHandlers.onHistoryEventSaved).toHaveBeenCalledTimes(1);
    });

    it('should reload the events when a transaction is added', async () => {
      set(container.currentDialog, createMock<DialogState>({ type: DIALOG_TYPES.TRANSACTION_FORM }));
      const view = mountContainer();
      const payload = { location: 'ethereum', txRef: '0xabc' };

      view.findComponent(stubs.TransactionFormDialog).vm.$emit('reload', payload);
      await nextTick();

      expect(eventHandlers.onTransactionAdded).toHaveBeenCalledWith(payload);
    });

    it('should route the missing rules dialog through the manager', async () => {
      set(container.currentDialog, createMock<DialogState>({ type: DIALOG_TYPES.MISSING_RULES }));
      const view = mountContainer();
      const dialog = view.findComponent(stubs.MissingRulesDialog);
      const editData = createMock<Extract<DialogState, { type: 'eventForm' }>['data']>({});

      dialog.vm.$emit('edit-event', editData);
      dialog.vm.$emit('add', { eventSubtype: 'a', eventType: 'b' });
      dialog.vm.$emit('redecode', { location: 'ethereum', txRef: '0xabc' });
      dialog.vm.$emit('dismiss');
      await nextTick();

      expect(container.show).toHaveBeenCalledWith({ data: editData, type: DIALOG_TYPES.EVENT_FORM });
      expect(container.show).toHaveBeenCalledWith({
        data: { eventSubtype: 'a', eventType: 'b' },
        type: DIALOG_TYPES.ADD_MISSING_RULE,
      });
      expect(eventHandlers.onRedecodeTransaction).toHaveBeenCalledWith({ location: 'ethereum', txRef: '0xabc' });
      expect(container.closeDialog).toHaveBeenCalledTimes(1);
    });

    it('should route the decoding status actions to their handlers', async () => {
      set(container.currentDialog, createMock<DialogState>({ type: DIALOG_TYPES.DECODING_STATUS }));
      const view = mountContainer();
      const dialog = view.findComponent(stubs.HistoryEventsDecodingStatusDialog);

      dialog.vm.$emit('redecode-all-events');
      dialog.vm.$emit('reset-undecoded-transactions');
      await nextTick();

      expect(eventHandlers.onRedecodeAllEvents).toHaveBeenCalledTimes(1);
      expect(eventHandlers.onResetUndecodedTransactions).toHaveBeenCalledTimes(1);
    });

    it('should report an accounting rule change to the page', async () => {
      const view = mountContainer();

      view.findComponent(stubs.AccountingRuleFormDialog).vm.$emit('refresh');
      await nextTick();

      expect(view.emitted('accounting-rule-refresh')).toHaveLength(1);
    });

    it('should report a match back to the page through the composable', () => {
      const view = mountContainer();

      options.onMovementMatched();
      options.onBridgeMatched();

      expect(view.emitted('movement-matched')).toHaveLength(1);
      expect(view.emitted('bridge-matched')).toHaveLength(1);
    });
  });

  describe('the potential matches dialogs', () => {
    it('should open the movement one from the matching list', async () => {
      set(container.currentDialog, createMock<DialogState>({ type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS }));
      const view = mountContainer();

      expect(view.findComponent(stubs.PotentialMatchesDialog).exists()).toBe(false);
      view.findComponent(stubs.MatchAssetMovementsDialog).vm.$emit('find-match', movement);
      await nextTick();

      expect(container.openMovementMatches).toHaveBeenCalledWith(movement);
    });

    it('should show the movement the composable is holding', async () => {
      set(container.movementSubject, movement);
      set(container.modelMovementMatchesOpen, true);
      const view = mountContainer();
      const dialog = view.findComponent(stubs.PotentialMatchesDialog);

      expect(dialog.exists()).toBe(true);
      dialog.vm.$emit('matched');
      dialog.vm.$emit('pinned');
      await nextTick();

      expect(container.onMovementMatched).toHaveBeenCalledTimes(1);
      expect(container.onMovementPinned).toHaveBeenCalledTimes(1);
    });

    it('should stay closed while the composable holds no movement', () => {
      set(container.modelMovementMatchesOpen, true);
      const view = mountContainer();

      expect(view.findComponent(stubs.PotentialMatchesDialog).exists()).toBe(false);
    });

    it('should open the bridge one from the matching list', async () => {
      set(container.currentDialog, createMock<DialogState>({ type: DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS }));
      const view = mountContainer();

      view.findComponent(stubs.MatchBridgeTransactionsDialog).vm.$emit('find-match', transaction);
      await nextTick();

      expect(container.openBridgeMatches).toHaveBeenCalledWith(transaction);
    });

    it('should show the transaction the composable is holding', async () => {
      set(container.bridgeSubject, transaction);
      set(container.modelBridgeMatchesOpen, true);
      const view = mountContainer();
      const dialog = view.findComponent(stubs.BridgePotentialMatchesDialog);

      expect(dialog.exists()).toBe(true);
      dialog.vm.$emit('matched');
      dialog.vm.$emit('pinned');
      await nextTick();

      expect(container.onBridgeMatched).toHaveBeenCalledTimes(1);
      expect(container.onBridgePinned).toHaveBeenCalledTimes(1);
    });
  });

  it('should expose the manager and both potential-match openers', () => {
    const view = mountContainer();

    expect(view.vm.show).toBe(container.show);
    expect(view.vm.showPotentialMatches).toBe(container.openMovementMatches);
    expect(view.vm.showBridgePotentialMatches).toBe(container.openBridgeMatches);
  });
});
