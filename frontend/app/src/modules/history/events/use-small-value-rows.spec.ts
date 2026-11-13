import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import type { SmallValueSubject } from '@/modules/history/events/use-small-value-events';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSmallValueRows } from '@/modules/history/events/use-small-value-rows';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

/** The rows the mocked classifier calls small, by asset. */
const smallAssets = vi.hoisted(() => new Set<string>());

vi.mock('@/modules/history/events/use-small-value-events', async () => {
  const { computed } = await import('vue');
  const { useSetting } = await import('@/modules/settings/use-setting');
  return {
    useSmallValueEvents: (): Record<string, unknown> => {
      const enabled = useSetting('deemphasizeSmallValueEvents');
      return {
        enabled: computed<boolean>(() => get(enabled)),
        isSmallValue: (subject: SmallValueSubject): boolean => smallAssets.has(subject.asset),
        threshold: computed<number>(() => 1),
      };
    },
  };
});

function row(id: string, asset: string): UnmatchedRow<unknown> {
  return createMock<UnmatchedRow<unknown>>({
    entry: createMock<HistoryEventEntry>({ amount: bigNumberify(1), asset, timestamp: 1_700_000_000_000 }),
    id,
  });
}

describe('useSmallValueRows', () => {
  const rows = [row('dust', 'DUST'), row('eth', 'ETH'), row('btc', 'BTC')];

  beforeEach(() => {
    setActivePinia(createPinia());
    smallAssets.clear();
    smallAssets.add('DUST');
  });

  it('should keep every row while small value events are not de-emphasized', () => {
    useSettingsRepo().updateFrontend({ hideSmallValueMovements: true });
    const { enabled, hiddenIds, visibleRows } = useSmallValueRows(rows);

    expect(get(enabled)).toBe(false);
    expect(get(visibleRows).map(item => item.id)).toEqual(['dust', 'eth', 'btc']);
    expect(get(hiddenIds).size).toBe(0);
  });

  it('should keep every row while hiding is off', () => {
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true });
    const { enabled, hiddenIds, visibleRows } = useSmallValueRows(rows);

    expect(get(enabled)).toBe(true);
    expect(get(visibleRows).map(item => item.id)).toEqual(['dust', 'eth', 'btc']);
    expect(get(hiddenIds).size).toBe(0);
  });

  it('should leave the small rows out while hiding is on', () => {
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true, hideSmallValueMovements: true });
    const { hiddenIds, visibleRows } = useSmallValueRows(rows);

    expect(get(visibleRows).map(item => item.id)).toEqual(['eth', 'btc']);
    expect([...get(hiddenIds)]).toEqual(['dust']);
  });

  it('should follow the rows it is given', () => {
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true, hideSmallValueMovements: true });
    const source = ref<UnmatchedRow<unknown>[]>([rows[1]]);
    const { hiddenIds, visibleRows } = useSmallValueRows(source);

    expect(get(hiddenIds).size).toBe(0);

    set(source, rows);

    expect(get(visibleRows).map(item => item.id)).toEqual(['eth', 'btc']);
    expect([...get(hiddenIds)]).toEqual(['dust']);
  });
});
