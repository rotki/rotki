import { describe, expect, it } from 'vitest';
import { useEventActionDescriptions } from '@/modules/history/events/action-picker/use-event-action-descriptions';

describe('useEventActionDescriptions', () => {
  it('should resolve a verb whose key matches its snake_case i18n key', () => {
    const { describe: describeVerb } = useEventActionDescriptions();
    expect(describeVerb('swap out')).toBe('history_event_action.picker.description.swap_out');
  });

  it('should resolve a verb whose key differs from its label', () => {
    const { describe: describeVerb } = useEventActionDescriptions();
    // label is "mev" but the serialized verb key is "mev reward"
    expect(describeVerb('mev reward')).toBe('history_event_action.picker.description.mev_reward');
  });

  it('should return undefined for an unknown verb key', () => {
    const { describe: describeVerb } = useEventActionDescriptions();
    expect(describeVerb('not a real verb')).toBeUndefined();
  });
});
