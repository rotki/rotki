import { describe, expect, it } from 'vitest';
import { useHistoryEventFilter } from '@/modules/history/events/use-events-filter';

describe('useHistoryEventFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useHistoryEventFilter();

    expect(get(filters)).toEqual({});
  });

  // The URL round-trip and the behaviour-carrying keys are asserted in
  // `history-event-fields.spec.ts`: both are derived from the fields, so they are proved against
  // the field list rather than against a second declaration that could disagree with it.
});
