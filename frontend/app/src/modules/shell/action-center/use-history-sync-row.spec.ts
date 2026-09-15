import type { EffectScope } from 'vue';
import type { ActionItem } from '@/modules/core/action-center/types';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistorySyncRow } from '@/modules/shell/action-center/use-history-sync-row';

const SYNCED_AT = Date.UTC(2026, 8, 15, 10, 30);

const hasTxAccounts = ref<boolean>(true);
const outOfSync = ref<boolean>(true);
const isNeverQueried = ref<boolean>(false);
const justUpdated = ref<boolean>(false);
const longQuery = ref<boolean>(false);
const processing = ref<boolean>(false);
const dismissedRecently = ref<boolean>(false);
const lastQueriedTimestamp = ref<number>(SYNCED_AT);
const dismiss = vi.fn<() => void>();
const recordAppVersion = vi.fn<() => void>();

vi.mock('@/modules/history/sync-status/use-history-sync-status', () => ({
  useHistorySyncStatus: (): object => ({
    dismiss,
    dismissedRecently,
    hasTxAccounts,
    isNeverQueried,
    justUpdated,
    lastQueriedTimestamp,
    longQuery,
    outOfSync,
    processing,
    recordAppVersion,
  }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<string> => ref('%Y-%m-%d %H:%M'),
}));

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): object => ({ scrambleTimestamp: (timestamp: number): number => timestamp }),
}));

let scope: EffectScope | undefined;

function rows(): ComputedRef<ActionItem[]> {
  scope = effectScope();
  const result = scope.run(() => useHistorySyncRow());
  assert(result);
  return result;
}

function onlyRow(): ActionItem {
  const [row, ...rest] = get(rows());
  assert(row);
  expect(rest).toHaveLength(0);
  return row;
}

describe('modules/shell/action-center/use-history-sync-row', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(hasTxAccounts, true);
    set(outOfSync, true);
    set(isNeverQueried, false);
    set(justUpdated, false);
    set(longQuery, false);
    set(processing, false);
    set(dismissedRecently, false);
    set(lastQueriedTimestamp, SYNCED_AT);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should record the app version once when created', () => {
    rows();
    expect(recordAppVersion).toHaveBeenCalledOnce();
  });

  it('should show no row for a user with no history sources', () => {
    set(hasTxAccounts, false);
    expect(get(rows())).toEqual([]);
  });

  it('should raise a dismissible row pointing at history events when out of sync', () => {
    const row = onlyRow();

    expect(row.id).toBe('history-sync');
    expect(row.count).toBe(1);
    expect(row.informational).toBe(false);
    expect(row.target).toEqual({ kind: 'route', to: { name: '/history/events/' } });
    expect(row.description).toBe('action_center.rows.history.sync.description::2026-09-15 10:30');

    const [option, ...others] = row.options;
    expect(others).toHaveLength(0);
    expect(option.id).toBe('dismiss');
    assert(option.target.kind === 'run');
    option.target.run();
    expect(dismiss).toHaveBeenCalledOnce();
  });

  it('should clear the row, titled as synced, when history is in sync', () => {
    set(outOfSync, false);
    const row = onlyRow();

    expect(row.count).toBe(0);
    expect(row.title).toBe('action_center.rows.history.sync.title_synced');
  });

  it('should keep a dismissed row listed as informational, with no dismiss of its own', () => {
    set(dismissedRecently, true);
    const row = onlyRow();

    expect(row.count).toBe(1);
    expect(row.informational).toBe(true);
    expect(row.options).toEqual([]);
  });

  it('should hold the row as loading while history is processing', () => {
    set(processing, true);
    expect(onlyRow().loading).toBe(true);
  });

  it('should say history was never downloaded', () => {
    set(isNeverQueried, true);
    const row = onlyRow();

    expect(row.title).toBe('action_center.rows.history.sync.title_never');
    expect(row.description).toBe('action_center.rows.history.sync.description_never');
  });

  it('should say the app was updated ahead of never downloaded', () => {
    set(isNeverQueried, true);
    set(justUpdated, true);
    const row = onlyRow();

    expect(row.title).toBe('action_center.rows.history.sync.title_updated');
    expect(row.description).toBe('action_center.rows.history.sync.description_updated');
  });

  it('should use the long-query description when history was synced long ago', () => {
    set(longQuery, true);
    expect(onlyRow().description).toBe('action_center.rows.history.sync.description_long::2026-09-15 10:30');
  });
});
