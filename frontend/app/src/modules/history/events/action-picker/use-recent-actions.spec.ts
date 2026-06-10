import { HistoryEventEntryType } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { useRecentActions } from '@/modules/history/events/action-picker/use-recent-actions';

describe('useRecentActions', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should record a picked verb at the front', () => {
    const { record, recent } = useRecentActions(() => HistoryEventEntryType.EVM_EVENT);

    record('swap out');
    record('receive');

    expect(get(recent)).toEqual(['receive', 'swap out']);
  });

  it('should move a re-picked verb to the front without duplicating it', () => {
    const { record, recent } = useRecentActions(() => HistoryEventEntryType.EVM_EVENT);

    record('a');
    record('b');
    record('a');

    expect(get(recent)).toEqual(['a', 'b']);
  });

  it('should rank a more frequently picked verb above a more recent one', () => {
    const { record, recent } = useRecentActions(() => HistoryEventEntryType.EVM_EVENT);

    record('a');
    record('a');
    record('b');

    // 'b' was picked last, but 'a' was picked more often, so frequency wins.
    expect(get(recent)).toEqual(['a', 'b']);
  });

  it('should display only the five top-ranked entries', () => {
    const { record, recent } = useRecentActions(() => HistoryEventEntryType.EVM_EVENT);

    for (const verb of ['a', 'b', 'c', 'd', 'e', 'f'])
      record(verb);

    expect(get(recent)).toEqual(['f', 'e', 'd', 'c', 'b']);
  });

  it('should persist recents across a fresh composable instance', async () => {
    useRecentActions(() => HistoryEventEntryType.EVM_EVENT).record('swap out');
    await nextTick();

    const { recent } = useRecentActions(() => HistoryEventEntryType.EVM_EVENT);
    expect(get(recent)).toEqual(['swap out']);
  });

  it('should scope recents per entry type', () => {
    const evm = useRecentActions(() => HistoryEventEntryType.EVM_EVENT);
    const block = useRecentActions(() => HistoryEventEntryType.ETH_BLOCK_EVENT);

    evm.record('swap out');
    block.record('block reward');

    expect(get(evm.recent)).toEqual(['swap out']);
    expect(get(block.recent)).toEqual(['block reward']);
  });

  it('should discard a persisted store with an incompatible schema version', () => {
    localStorage.setItem(
      'rotki.history.recent-actions',
      JSON.stringify({ entries: { [HistoryEventEntryType.EVM_EVENT]: ['stale'] }, schemaVersion: 0 }),
    );

    const { recent } = useRecentActions(() => HistoryEventEntryType.EVM_EVENT);
    expect(get(recent)).toEqual([]);
  });
});
