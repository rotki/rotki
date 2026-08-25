import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { toTableSource } from '@/modules/history/events/view-projections';

const groups = createMock<Collection<HistoryEventRow>>({ data: [], found: 3, limit: 10, total: 3 });
const requestPayload = createMock<HistoryEventRequestPayload>({ limit: 10, offset: 0 });

function toggles(overrides: Partial<HistoryEventsToggles> = {}): HistoryEventsToggles {
  return { matchExactEvents: false, showIgnoredAssets: false, stateMarkers: [], ...overrides };
}

describe('toTableSource', () => {
  it('should exclude ignored assets unless the user asked to see them', () => {
    expect(toTableSource({ groupLoading: false, groups, requestPayload, toggles: toggles() }).excludeIgnored)
      .toBe(true);

    expect(toTableSource({
      groupLoading: false,
      groups,
      requestPayload,
      toggles: toggles({ showIgnoredAssets: true }),
    }).excludeIgnored).toBe(false);
  });

  it('should withhold the filter payload while match-exact is off', () => {
    const source = toTableSource({ groupLoading: false, groups, requestPayload, toggles: toggles() });

    expect(source.requestPayload).toBeUndefined();
  });

  it('should pass the filter payload down once match-exact is on', () => {
    const source = toTableSource({
      groupLoading: false,
      groups,
      requestPayload,
      toggles: toggles({ matchExactEvents: true }),
    });

    expect(source.requestPayload).toBe(requestPayload);
  });

  it('should pass the group page and its loading state through unchanged', () => {
    const source = toTableSource({
      groupLoading: true,
      groups,
      identifiers: ['1', '2'],
      requestPayload,
      toggles: toggles(),
    });

    expect(source.groups).toBe(groups);
    expect(source.groupLoading).toBe(true);
    expect(source.identifiers).toStrictEqual(['1', '2']);
  });

  it('should load the whole page when no identifiers are given', () => {
    const source = toTableSource({ groupLoading: false, groups, requestPayload, toggles: toggles() });

    expect(source.identifiers).toBeUndefined();
  });
});
