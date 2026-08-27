import type { UseHistoryEventsFiltersChipsOptions } from '@/modules/history/events/use-history-events-filters-chips';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import HistoryEventsFiltersChips from '@/modules/history/events/HistoryEventsFiltersChips.vue';

const chips = {
  allDuplicatesResolved: ref<boolean>(false),
  confirmFixDuplicate: vi.fn(),
  duplicateChangesMessage: ref<string>(''),
  duplicateChipText: ref<string>('Viewing auto fixable duplicates'),
  fixLoading: ref<boolean>(false),
  hasDuplicateChanges: ref<boolean>(false),
  isAutoFixable: ref<boolean>(true),
  refreshDuplicateView: vi.fn(),
  removeAccountingEventParam: vi.fn(),
  removeDuplicateEventsParam: vi.fn(),
  removeMissingAcquisitionParam: vi.fn(),
  removeNegativeBalanceParam: vi.fn(),
  showAccountingEvent: ref<boolean>(false),
  showDuplicates: ref<boolean>(false),
  showMissingAcquisition: ref<boolean>(false),
  showNegativeBalance: ref<boolean>(false),
};

let options: UseHistoryEventsFiltersChipsOptions;

vi.mock('@/modules/history/events/use-history-events-filters-chips', () => ({
  useHistoryEventsFiltersChips: (opts: UseHistoryEventsFiltersChipsOptions): unknown => {
    options = opts;
    return chips;
  },
}));

describe('modules/history/events/HistoryEventsFiltersChips', () => {
  let wrapper: VueWrapper | undefined;

  function mountChips(props: Record<string, unknown> = {}): VueWrapper {
    wrapper = mount(HistoryEventsFiltersChips, { props });
    return wrapper;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(chips.allDuplicatesResolved, false);
    set(chips.duplicateChangesMessage, '');
    set(chips.duplicateChipText, 'Viewing auto fixable duplicates');
    set(chips.fixLoading, false);
    set(chips.hasDuplicateChanges, false);
    set(chips.isAutoFixable, true);
    set(chips.showAccountingEvent, false);
    set(chips.showDuplicates, false);
    set(chips.showMissingAcquisition, false);
    set(chips.showNegativeBalance, false);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should forward its props and its refresh event to the composable', () => {
    const view = mountChips({
      duplicateHandlingStatus: DuplicateHandlingStatus.MANUAL_REVIEW,
      groupIdentifiers: ['g1', 'g2'],
    });

    expect(options.groupIdentifiers()).toStrictEqual(['g1', 'g2']);
    expect(options.duplicateHandlingStatus()).toBe(DuplicateHandlingStatus.MANUAL_REVIEW);

    options.onRefresh();

    expect(view.emitted('refresh')).toHaveLength(1);
  });

  it('should render no chip while nothing is filtered', () => {
    const view = mountChips();

    expect(view.find('[data-testid="missing-acquisition-chip"]').exists()).toBe(false);
    expect(view.find('[data-testid="negative-balance-chip"]').exists()).toBe(false);
    expect(view.find('[data-testid="accounting-divergence-chip"]').exists()).toBe(false);
    expect(view.find('[data-testid="duplicate-events-chip"]').exists()).toBe(false);
  });

  it.each([
    ['missing-acquisition-chip', 'showMissingAcquisition', 'removeMissingAcquisitionParam'],
    ['negative-balance-chip', 'showNegativeBalance', 'removeNegativeBalanceParam'],
    ['accounting-divergence-chip', 'showAccountingEvent', 'removeAccountingEventParam'],
    ['duplicate-events-chip', 'showDuplicates', 'removeDuplicateEventsParam'],
  ] as const)('should close the %s through the composable', async (testId, flag, remover) => {
    set(chips[flag], true);
    set(chips.isAutoFixable, false);
    const view = mountChips();

    const chip = view.find(`[data-testid="${testId}"]`);
    expect(chip.exists()).toBe(true);
    await chip.find('button').trigger('click');

    expect(chips[remover]).toHaveBeenCalledTimes(1);
  });

  it('should label the duplicate chip with what the composable says it is showing', () => {
    set(chips.showDuplicates, true);
    set(chips.duplicateChipText, 'Viewing duplicates for manual review');
    const view = mountChips();

    expect(view.find('[data-testid="duplicate-events-chip"]').text())
      .toContain('Viewing duplicates for manual review');
  });

  describe('fixing every shown duplicate', () => {
    beforeEach(() => {
      set(chips.showDuplicates, true);
    });

    it('should offer the fix while the bucket is auto fixable and has not drifted', async () => {
      const view = mountChips();

      await view.find('[data-testid="duplicate-fix-all"]').trigger('click');

      expect(chips.confirmFixDuplicate).toHaveBeenCalledTimes(1);
    });

    it('should not offer the fix for the manual review bucket', () => {
      set(chips.isAutoFixable, false);
      const view = mountChips();

      expect(view.find('[data-testid="duplicate-fix-all"]').exists()).toBe(false);
    });

    it('should not offer the fix while the backend has drifted from the URL', () => {
      set(chips.hasDuplicateChanges, true);
      const view = mountChips();

      expect(view.find('[data-testid="duplicate-fix-all"]').exists()).toBe(false);
    });

    it('should show the fix as loading while one is in flight', () => {
      set(chips.fixLoading, true);
      const view = mountChips();

      const fix = view.findAllComponents({ name: 'RuiButton' })
        .find(button => button.attributes('data-testid') === 'duplicate-fix-all');

      expect(fix?.props('loading')).toBe(true);
    });
  });

  describe('the drift notice', () => {
    beforeEach(() => {
      set(chips.showDuplicates, true);
      set(chips.hasDuplicateChanges, true);
      set(chips.duplicateChangesMessage, '2 resolved, 1 added');
    });

    it('should stay hidden while the URL and the backend agree', () => {
      set(chips.hasDuplicateChanges, false);
      const view = mountChips();

      expect(view.find('[data-testid="duplicate-changes"]').exists()).toBe(false);
    });

    it('should show the message the composable produced', () => {
      const view = mountChips();

      expect(view.find('[data-testid="duplicate-changes"]').text()).toContain('2 resolved, 1 added');
    });

    it('should offer a refresh while some duplicates remain', async () => {
      const view = mountChips();

      const button = view.find('[data-testid="duplicate-refresh"]');
      expect(button.text()).toBe('common.refresh');
      await button.trigger('click');

      expect(chips.refreshDuplicateView).toHaveBeenCalledTimes(1);
    });

    it('should offer to clear the filter once nothing is left to show', () => {
      set(chips.allDuplicatesResolved, true);
      const view = mountChips();

      expect(view.find('[data-testid="duplicate-refresh"]').text())
        .toBe('customized_event_duplicates.chips.clear_filter');
    });
  });
});
