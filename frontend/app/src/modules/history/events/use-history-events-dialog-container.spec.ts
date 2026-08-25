import type { DialogState } from '@/modules/history/events/dialog-manager/types';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';
import {
  useHistoryEventsDialogContainer,
  type UseHistoryEventsDialogContainerReturn,
} from '@/modules/history/events/use-history-events-dialog-container';

const closeDialog = vi.fn();
const show = vi.fn().mockResolvedValue(undefined);
const currentDialog = ref<DialogState>({ type: 'closed' });

vi.mock('@/modules/history/events/dialog-manager/use-history-events-dialog-manager', () => ({
  useHistoryEventsDialogManager: (): Record<string, unknown> => ({ closeDialog, currentDialog, show }),
}));

const onMovementMatched = vi.fn();
const onBridgeMatched = vi.fn();

interface Harness {
  wrapper: VueWrapper;
  container: UseHistoryEventsDialogContainerReturn;
}

function mountContainer(): Harness {
  let container!: UseHistoryEventsDialogContainerReturn;
  const Comp = defineComponent({
    setup(): () => null {
      container = useHistoryEventsDialogContainer({ onBridgeMatched, onMovementMatched });
      return (): null => null;
    },
  });
  const wrapper = mount(Comp);
  return { container, wrapper };
}

const movement = createMock<UnmatchedAssetMovement>({ groupIdentifier: 'group-a' });
const transaction = createMock<UnmatchedBridgeTransaction>({ groupIdentifier: 'group-b' });

describe('useHistoryEventsDialogContainer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(currentDialog, { type: 'closed' });
    show.mockResolvedValue(undefined);
  });

  describe('reading a form back off the open dialog', () => {
    it('should hand the event form the data the manager holds', () => {
      const data = createMock<Extract<DialogState, { type: 'eventForm' }>['data']>({});
      set(currentDialog, { data, type: DIALOG_TYPES.EVENT_FORM });
      const { container } = mountContainer();

      expect(get(container.modelFormData)).toBe(data);
    });

    it('should hand the event form nothing while another dialog is open', () => {
      set(currentDialog, { data: undefined, type: DIALOG_TYPES.PROTOCOL_CACHE });
      const { container } = mountContainer();

      expect(get(container.modelFormData)).toBeUndefined();
    });

    it('should treat a write to the event form as a close', () => {
      const { container } = mountContainer();

      set(container.modelFormData, undefined);

      expect(closeDialog).toHaveBeenCalledTimes(1);
    });

    it('should hand the missing rules dialog the data the manager holds', () => {
      const data = createMock<Extract<DialogState, { type: 'missingRules' }>['data']>({});
      set(currentDialog, { data, type: DIALOG_TYPES.MISSING_RULES });
      const { container } = mountContainer();

      expect(get(container.modelMissingRule)).toBe(data);
    });

    it('should treat a write to the missing rules dialog as a close', () => {
      const { container } = mountContainer();

      set(container.modelMissingRule, undefined);

      expect(closeDialog).toHaveBeenCalledTimes(1);
    });
  });

  describe('the dialogs that are open because they are rendered', () => {
    it('should always read as open', () => {
      const { container } = mountContainer();

      expect(get(container.modelDialogOpen)).toBe(true);
    });

    it('should close the manager dialog when written to', () => {
      const { container } = mountContainer();

      set(container.modelDialogOpen, false);

      expect(closeDialog).toHaveBeenCalledTimes(1);
    });
  });

  describe('the decoding status dialog', () => {
    it('should not be persistent by default', () => {
      set(currentDialog, { data: { persistent: false }, type: DIALOG_TYPES.DECODING_STATUS });
      const { container } = mountContainer();

      expect(get(container.decodingStatusPersistent)).toBe(false);
    });

    it('should be persistent when the manager asked for it', () => {
      set(currentDialog, { data: { persistent: true }, type: DIALOG_TYPES.DECODING_STATUS });
      const { container } = mountContainer();

      expect(get(container.decodingStatusPersistent)).toBe(true);
    });

    it('should not be persistent while a different dialog is open', () => {
      set(currentDialog, { data: undefined, type: DIALOG_TYPES.PROTOCOL_CACHE });
      const { container } = mountContainer();

      expect(get(container.decodingStatusPersistent)).toBe(false);
    });
  });

  describe('the add transaction form', () => {
    it('should read the payload the manager holds', () => {
      const data = { associatedAddress: '0x1', blockchain: 'eth', txRef: '0xabc' };
      set(currentDialog, { data, type: DIALOG_TYPES.TRANSACTION_FORM });
      const { container } = mountContainer();

      expect(get(container.modelAddTransaction)).toStrictEqual(data);
    });

    it('should push an edited payload back through the manager', () => {
      const { container } = mountContainer();
      const data = { associatedAddress: '0x2', blockchain: 'eth', txRef: '0xdef' };

      set(container.modelAddTransaction, data);

      expect(show).toHaveBeenCalledWith({ data, type: DIALOG_TYPES.TRANSACTION_FORM });
      expect(closeDialog).not.toHaveBeenCalled();
    });

    it('should close the dialog when the payload is cleared', () => {
      const { container } = mountContainer();

      set(container.modelAddTransaction, undefined);

      expect(closeDialog).toHaveBeenCalledTimes(1);
      expect(show).not.toHaveBeenCalled();
    });
  });

  describe('the movement potential matches dialog', () => {
    it('should stay closed until a movement is chosen', () => {
      const { container } = mountContainer();

      expect(get(container.movementSubject)).toBeUndefined();
      expect(get(container.modelMovementMatchesOpen)).toBe(false);
    });

    it('should open on the movement it is given', () => {
      const { container } = mountContainer();

      container.openMovementMatches(movement);

      expect(get(container.movementSubject)).toBe(movement);
      expect(get(container.modelMovementMatchesOpen)).toBe(true);
    });

    it('should drop the movement and report the match', () => {
      const { container } = mountContainer();
      container.openMovementMatches(movement);

      container.onMovementMatched();

      expect(get(container.movementSubject)).toBeUndefined();
      expect(onMovementMatched).toHaveBeenCalledTimes(1);
      expect(closeDialog).not.toHaveBeenCalled();
    });

    it('should close the dialog behind it when the list is pinned', () => {
      const { container } = mountContainer();
      container.openMovementMatches(movement);

      container.onMovementPinned();

      expect(get(container.movementSubject)).toBeUndefined();
      expect(closeDialog).toHaveBeenCalledTimes(1);
      expect(onMovementMatched).not.toHaveBeenCalled();
    });
  });

  describe('the bridge potential matches dialog', () => {
    it('should open on the transaction it is given', () => {
      const { container } = mountContainer();

      container.openBridgeMatches(transaction);

      expect(get(container.bridgeSubject)).toBe(transaction);
      expect(get(container.modelBridgeMatchesOpen)).toBe(true);
    });

    it('should drop the transaction and report the match', () => {
      const { container } = mountContainer();
      container.openBridgeMatches(transaction);

      container.onBridgeMatched();

      expect(get(container.bridgeSubject)).toBeUndefined();
      expect(onBridgeMatched).toHaveBeenCalledTimes(1);
    });

    it('should close the dialog behind it when the list is pinned', () => {
      const { container } = mountContainer();
      container.openBridgeMatches(transaction);

      container.onBridgePinned();

      expect(get(container.bridgeSubject)).toBeUndefined();
      expect(closeDialog).toHaveBeenCalledTimes(1);
      expect(onBridgeMatched).not.toHaveBeenCalled();
    });

    it('should keep the two dialogs apart', () => {
      const { container } = mountContainer();

      container.openMovementMatches(movement);
      container.onBridgeMatched();

      expect(get(container.movementSubject)).toBe(movement);
      expect(get(container.modelMovementMatchesOpen)).toBe(true);
    });
  });
});
