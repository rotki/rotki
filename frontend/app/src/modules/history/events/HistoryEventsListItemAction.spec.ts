import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import HistoryEventAction from '@/modules/history/events/HistoryEventAction.vue';
import HistoryEventsListItemAction from '@/modules/history/events/HistoryEventsListItemAction.vue';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry } from '@/modules/history/events/schemas';

/**
 * Seam: every action on an event goes through its one overflow menu, missing rule or not, so the
 * row passes the menu what may be done and turns its choices into the row's own events.
 */
describe('modules/history/events/HistoryEventsListItemAction', () => {
  let wrapper: VueWrapper | undefined;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  const unlinkConfirm = { message: 'Unlink these?', title: 'Unlink' };

  function mountAction(options: { canUnlink?: boolean; missingRule?: boolean; item?: HistoryEventEntry; group?: HistoryEventEntry[] }): VueWrapper {
    const item = options.item ?? createMock<HistoryEventEntry>({
      entryType: HistoryEventEntryType.HISTORY_EVENT,
      eventAccountingRuleStatus: options.missingRule
        ? HistoryEventAccountingRuleStatus.NOT_PROCESSED
        : HistoryEventAccountingRuleStatus.HAS_RULE,
      identifier: 1,
    });

    wrapper = mount(HistoryEventsListItemAction, {
      global: { provide: libraryDefaults },
      props: {
        completeGroupEvents: options.group ?? [item],
        index: 0,
        item,
        unlinkConfirm: options.canUnlink ? unlinkConfirm : undefined,
      },
    });
    return wrapper;
  }

  it('should keep the menu, with unlink in it, when a missing rule shows its warning', () => {
    const action = mountAction({ canUnlink: true, missingRule: true });

    expect(action.findComponent(HistoryEventAction).props('unlinkConfirm')).toStrictEqual(unlinkConfirm);
  });

  it('should offer unlink through the menu when the rule is present', () => {
    const action = mountAction({ canUnlink: true });

    expect(action.findComponent(HistoryEventAction).props('unlinkConfirm')).toStrictEqual(unlinkConfirm);
  });

  it('should offer no unlink at all for a row that cannot be unlinked', () => {
    const action = mountAction({ missingRule: true });

    expect(action.findComponent(HistoryEventAction).props('unlinkConfirm')).toBeUndefined();
  });

  it('should have the menu ask before deleting the event', () => {
    const action = mountAction({});

    expect(action.findComponent(HistoryEventAction).props('deleteConfirm')).toStrictEqual({
      confirmLabel: 'common.actions.delete',
      message: 'transactions.events.confirmation.delete.message',
      title: 'transactions.events.confirmation.delete.title',
    });
  });

  it('should ask about excluding a lone evm event from accounting, which cannot be deleted from its transaction', async () => {
    const item = createMock<HistoryEventEntry>({
      entryType: HistoryEventEntryType.EVM_EVENT,
      eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.HAS_RULE,
      identifier: 3,
    });
    const action = mountAction({ item });

    expect(action.findComponent(HistoryEventAction).props('deleteConfirm')).toMatchObject({
      message: 'transactions.events.confirmation.ignore.message',
      title: 'transactions.events.confirmation.ignore.title',
    });

    action.findComponent(HistoryEventAction).vm.$emit('delete');
    await nextTick();

    expect(action.emitted('delete-event')).toStrictEqual([[{ event: item, type: 'ignore' }]]);
  });

  it('should turn the menu\'s unlink into the row\'s unlink', async () => {
    const action = mountAction({ canUnlink: true });

    action.findComponent(HistoryEventAction).vm.$emit('unlink');
    await nextTick();

    expect(action.emitted('unlink-event')).toHaveLength(1);
  });

  it('should open the event for editing from the menu', async () => {
    const action = mountAction({});

    action.findComponent(HistoryEventAction).vm.$emit('edit');
    await nextTick();

    expect(action.emitted('edit-event')).toHaveLength(1);
  });

  it('should delete the event once the menu\'s question is accepted', async () => {
    const action = mountAction({});

    action.findComponent(HistoryEventAction).vm.$emit('delete');
    await nextTick();

    expect(action.emitted('delete-event')).toStrictEqual([[{ ids: [1], type: 'delete' }]]);
  });
});
