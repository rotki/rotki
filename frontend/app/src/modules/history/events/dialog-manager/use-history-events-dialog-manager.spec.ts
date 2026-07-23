import type { GroupEventData } from '@/modules/history/management/forms/form-types';
import { assert } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRouter } from 'vue-router';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';
import { PinnedNames } from '@/modules/session/types';
import { useHistoryEventsDialogManager } from './use-history-events-dialog-manager';

const push = vi.fn();

describe('useHistoryEventsDialogManager', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    push.mockClear();
    vi.mocked(useRouter).mockReturnValue(createMock<ReturnType<typeof useRouter>>({ push }));
  });

  it('should start closed', () => {
    const { currentDialog } = useHistoryEventsDialogManager();
    expect(get(currentDialog)).toEqual({ type: 'closed' });
  });

  it('should open the event form with its data', async () => {
    const { currentDialog, show } = useHistoryEventsDialogManager();
    const data = createMock<GroupEventData>();
    await show({ data, type: DIALOG_TYPES.EVENT_FORM });
    const dialog = get(currentDialog);
    expect(dialog.type).toBe(DIALOG_TYPES.EVENT_FORM);
    assert(dialog.type === DIALOG_TYPES.EVENT_FORM);
    expect(dialog.data).toBe(data);
  });

  it('should default the transaction form data when none is given', async () => {
    const { currentDialog, show } = useHistoryEventsDialogManager();
    await show({ type: DIALOG_TYPES.TRANSACTION_FORM });
    expect(get(currentDialog)).toEqual({
      data: { associatedAddress: '', blockchain: '', txRef: '' },
      type: DIALOG_TYPES.TRANSACTION_FORM,
    });
  });

  it('should map add-transaction to an empty transaction form', async () => {
    const { currentDialog, show } = useHistoryEventsDialogManager();
    await show({ type: DIALOG_TYPES.ADD_TRANSACTION });
    expect(get(currentDialog)).toEqual({
      data: { associatedAddress: '', blockchain: '', txRef: '' },
      type: DIALOG_TYPES.TRANSACTION_FORM,
    });
  });

  it('should carry the persistent flag into the decoding-status dialog', async () => {
    const { currentDialog, show } = useHistoryEventsDialogManager();
    await show({ persistent: true, type: DIALOG_TYPES.DECODING_STATUS });
    expect(get(currentDialog)).toEqual({ data: { persistent: true }, type: DIALOG_TYPES.DECODING_STATUS });
  });

  it('should open dataless dialogs', async () => {
    const { currentDialog, show } = useHistoryEventsDialogManager();
    await show({ type: DIALOG_TYPES.PROTOCOL_CACHE });
    expect(get(currentDialog)).toEqual({ data: undefined, type: DIALOG_TYPES.PROTOCOL_CACHE });
  });

  it('should navigate to the accounting settings for add-missing-rule', async () => {
    const { show } = useHistoryEventsDialogManager();
    await show({
      data: { counterparty: 'cp', eventIds: [5], eventSubtype: 'sub', eventType: 'type' },
      type: DIALOG_TYPES.ADD_MISSING_RULE,
    });
    expect(push).toHaveBeenCalledWith({
      path: '/settings/accounting',
      query: { 'add-rule': 'true', 'counterparty': 'cp', 'eventId': '5', 'eventSubtype': 'sub', 'eventType': 'type' },
    });
  });

  it('should focus the pinned panel instead of opening the conflicts dialog when already pinned', async () => {
    const visibility = useAreaVisibilityStore();
    const { showPinned } = storeToRefs(visibility);
    visibility.pinPanel({ name: PinnedNames.INTERNAL_TX_CONFLICTS, props: {} });
    set(showPinned, false);

    const { currentDialog, show } = useHistoryEventsDialogManager();
    await show({ type: DIALOG_TYPES.INTERNAL_TX_CONFLICTS });

    expect(get(showPinned)).toBe(true);
    expect(get(currentDialog)).toEqual({ type: 'closed' });
  });

  it('should open the conflicts dialog when not pinned', async () => {
    const { currentDialog, show } = useHistoryEventsDialogManager();
    await show({ type: DIALOG_TYPES.INTERNAL_TX_CONFLICTS });
    expect(get(currentDialog)).toEqual({ data: undefined, type: DIALOG_TYPES.INTERNAL_TX_CONFLICTS });
  });

  it('should close an open dialog', async () => {
    const { closeDialog, currentDialog, show } = useHistoryEventsDialogManager();
    await show({ type: DIALOG_TYPES.PROTOCOL_CACHE });
    expect(get(currentDialog).type).toBe(DIALOG_TYPES.PROTOCOL_CACHE);
    closeDialog();
    expect(get(currentDialog)).toEqual({ type: 'closed' });
  });
});
