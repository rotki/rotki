import type { LocationQuery } from 'vue-router';
import type { PanelRow } from '@/modules/history/data-issues/use-data-issues-panel-list';
import { createMock } from '@test/utils/create-mock';
import { get, set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useDataIssuesPanelSelection } from '@/modules/history/data-issues/use-data-issues-panel-selection';
import { HighlightTargetTypes } from '@/modules/history/events/use-history-event-navigation';

const route = ref<{ query: LocationQuery }>({ query: {} });
const push = vi.fn();
const replace = vi.fn();
const clearHighlightTarget = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: (): unknown => route,
  useRouter: (): unknown => ({ push, replace }),
}));

vi.mock('@/modules/history/events/use-history-event-navigation', () => ({
  HighlightTargetTypes: { NEGATIVE_BALANCE: 'negativeBalance' },
  useHistoryEventNavigation: (): Record<string, unknown> => ({ clearHighlightTarget }),
}));

/** A row whose card would be highlighted for `eventIdentifier`. */
function row(eventIdentifier: number | undefined): PanelRow {
  return createMock<PanelRow>({
    description: { amounts: {}, eventIdentifier, messageKey: 'k', shortMessageKey: 'k' },
  });
}

describe('useDataIssuesPanelSelection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(route, { query: {} });
  });

  it('should report no selection when the query carries no highlight', () => {
    const { activeEventIdentifier, hasActiveSelection } = useDataIssuesPanelSelection();

    expect(get(activeEventIdentifier)).toBeUndefined();
    expect(get(hasActiveSelection)).toBe(false);
  });

  it('should read the highlighted event from the query', () => {
    set(route, { query: { highlightedNegativeBalanceEvent: '42' } });
    const { activeEventIdentifier, hasActiveSelection } = useDataIssuesPanelSelection();

    expect(get(activeEventIdentifier)).toBe(42);
    expect(get(hasActiveSelection)).toBe(true);
  });

  it('should take the first value when the query repeats the parameter', () => {
    set(route, { query: { highlightedNegativeBalanceEvent: ['7', '9'] } });
    const { activeEventIdentifier } = useDataIssuesPanelSelection();

    expect(get(activeEventIdentifier)).toBe(7);
  });

  it('should reject a non-numeric highlight rather than selecting NaN', () => {
    set(route, { query: { highlightedNegativeBalanceEvent: 'abc' } });
    const { activeEventIdentifier, hasActiveSelection } = useDataIssuesPanelSelection();

    expect(get(activeEventIdentifier)).toBeUndefined();
    expect(get(hasActiveSelection)).toBe(false);
  });

  it('should reject zero and negative identifiers', () => {
    set(route, { query: { highlightedNegativeBalanceEvent: '0' } });
    const { activeEventIdentifier } = useDataIssuesPanelSelection();
    expect(get(activeEventIdentifier)).toBeUndefined();

    set(route, { query: { highlightedNegativeBalanceEvent: '-3' } });
    expect(get(activeEventIdentifier)).toBeUndefined();
  });

  it('should follow the query, so clearing the highlight elsewhere deselects the card', () => {
    set(route, { query: { highlightedNegativeBalanceEvent: '42' } });
    const { hasActiveSelection } = useDataIssuesPanelSelection();
    expect(get(hasActiveSelection)).toBe(true);

    set(route, { query: {} });

    expect(get(hasActiveSelection)).toBe(false);
  });

  it('should mark only the row whose event is highlighted', () => {
    set(route, { query: { highlightedNegativeBalanceEvent: '42' } });
    const { isActiveRow } = useDataIssuesPanelSelection();

    expect(isActiveRow(row(42))).toBe(true);
    expect(isActiveRow(row(43))).toBe(false);
  });

  it('should not mark a row that has no related event', () => {
    set(route, { query: {} });
    const { isActiveRow } = useDataIssuesPanelSelection();

    expect(isActiveRow(row(undefined))).toBe(false);
  });

  it('should push the target when going to an event', async () => {
    const { goToEvent } = useDataIssuesPanelSelection();

    await goToEvent({ path: '/history/events' });

    expect(push).toHaveBeenCalledWith({ path: '/history/events' });
  });

  it('should strip both highlight params and keep the rest of the query', async () => {
    set(route, {
      query: { highlightedNegativeBalanceEvent: '42', page: '2', targetGroupIdentifier: '0xabc' },
    });
    const { clearSelection } = useDataIssuesPanelSelection();

    await clearSelection();

    expect(clearHighlightTarget).toHaveBeenCalledWith(HighlightTargetTypes.NEGATIVE_BALANCE);
    expect(replace).toHaveBeenCalledWith({ query: { page: '2' } });
  });

  it('should clear the paging target even when no event is highlighted', async () => {
    set(route, { query: { targetGroupIdentifier: '0xabc' } });
    const { clearSelection } = useDataIssuesPanelSelection();

    await clearSelection();

    expect(replace).toHaveBeenCalledWith({ query: {} });
  });

  it('should not navigate when there is nothing to clear', async () => {
    const { clearSelection } = useDataIssuesPanelSelection();

    await clearSelection();

    expect(clearHighlightTarget).toHaveBeenCalledOnce();
    expect(replace).not.toHaveBeenCalled();
  });
});
