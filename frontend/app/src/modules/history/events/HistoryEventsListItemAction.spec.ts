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

  function mountAction(options: { canUnlink?: boolean; missingRule?: boolean }): VueWrapper {
    const item = createMock<HistoryEventEntry>({
      eventAccountingRuleStatus: options.missingRule
        ? HistoryEventAccountingRuleStatus.NOT_PROCESSED
        : HistoryEventAccountingRuleStatus.HAS_RULE,
      identifier: 1,
    });

    wrapper = mount(HistoryEventsListItemAction, {
      global: { provide: libraryDefaults },
      props: { canUnlink: options.canUnlink, completeGroupEvents: [item], index: 0, item },
    });
    return wrapper;
  }

  it('should keep the menu, with unlink in it, when a missing rule shows its warning', () => {
    const action = mountAction({ canUnlink: true, missingRule: true });

    expect(action.findComponent(HistoryEventAction).props('canUnlink')).toBe(true);
  });

  it('should offer unlink through the menu when the rule is present', () => {
    const action = mountAction({ canUnlink: true });

    expect(action.findComponent(HistoryEventAction).props('canUnlink')).toBe(true);
  });

  it('should offer no unlink at all for a row that cannot be unlinked', () => {
    const action = mountAction({ missingRule: true });

    expect(action.findComponent(HistoryEventAction).props('canUnlink')).toBeFalsy();
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

  it('should ask to delete the event from the menu', async () => {
    const action = mountAction({});

    action.findComponent(HistoryEventAction).vm.$emit('delete');
    await nextTick();

    expect(action.emitted('delete-event')).toHaveLength(1);
  });
});
