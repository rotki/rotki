import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import HistoryEventAction from '@/modules/history/events/HistoryEventAction.vue';
import HistoryEventsListItemAction from '@/modules/history/events/HistoryEventsListItemAction.vue';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry } from '@/modules/history/events/schemas';

/**
 * Seam: which unlink affordance the row offers. A missing accounting rule replaces the overflow
 * menu with the warning button, so an unlinkable row needs its own unlink button there or the
 * action is unreachable without expanding the subgroup.
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

  it('should offer unlink as its own button when a missing rule hides the menu', async () => {
    const action = mountAction({ canUnlink: true, missingRule: true });

    expect(action.findComponent(HistoryEventAction).exists()).toBe(false);
    await action.find('[data-testid="row-unlink"]').trigger('click');
    expect(action.emitted('unlink-event')).toHaveLength(1);
  });

  it('should offer unlink through the menu when the rule is present', () => {
    const action = mountAction({ canUnlink: true });

    expect(action.find('[data-testid="row-unlink"]').exists()).toBe(false);
    expect(action.findComponent(HistoryEventAction).props('canUnlink')).toBe(true);
  });

  it('should offer no unlink at all for a row that cannot be unlinked', () => {
    const action = mountAction({ missingRule: true });

    expect(action.find('[data-testid="row-unlink"]').exists()).toBe(false);
  });
});
