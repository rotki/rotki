import type { Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { EntryMeta } from '@/modules/history/meta';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useIgnore } from '@/modules/history/use-ignore';

interface TestItem extends EntryMeta {
  groupIdentifier: string;
  ignoredInAccounting: boolean;
}

const { spies } = vi.hoisted(() => ({
  spies: {
    ignoreActions: vi.fn(),
    unignoreActions: vi.fn(),
  },
}));

vi.mock('@/modules/history/api/use-history-ignoring-api', () => ({
  useHistoryIgnoringApi: (): object => ({
    ignoreActions: spies.ignoreActions,
    unignoreActions: spies.unignoreActions,
  }),
}));

function item(groupIdentifier: string, ignoredInAccounting = false): TestItem {
  return { groupIdentifier, ignoredInAccounting };
}

function setup(items: TestItem[]): {
  ignore: (ignored: boolean) => Promise<ActionStatus>;
  ignoreSingle: (item: TestItem, ignored: boolean) => Promise<ActionStatus>;
  toggle: (item: TestItem) => Promise<ActionStatus>;
  refresh: ReturnType<typeof vi.fn>;
  selected: Ref<TestItem[]>;
} {
  const selected = shallowRef<TestItem[]>(items);
  const refresh = vi.fn();
  const api = useIgnore<TestItem>({ toData: i => i.groupIdentifier }, selected, refresh);
  return { ...api, refresh, selected };
}

describe('useIgnore', () => {
  beforeEach(() => {
    spies.ignoreActions.mockResolvedValue(true);
    spies.unignoreActions.mockResolvedValue(true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should ignore only the not-yet-ignored items and dedupe payload', async () => {
    const { ignore, refresh, selected } = setup([
      item('a'),
      item('a'), // duplicate group identifier
      item('b'),
      item('c', true), // already ignored -> excluded when ignoring
    ]);

    await ignore(true);

    expect(spies.ignoreActions).toHaveBeenCalledWith({ data: ['a', 'b'] });
    expect(spies.unignoreActions).not.toHaveBeenCalled();
    expect(refresh).toHaveBeenCalledOnce();
    expect(get(selected)).toEqual([]);
  });

  it('should unignore only the currently-ignored items', async () => {
    const { ignore, refresh, selected } = setup([
      item('a', true),
      item('b', false), // not ignored -> excluded when unignoring
    ]);

    await ignore(false);

    expect(spies.unignoreActions).toHaveBeenCalledWith({ data: ['a'] });
    expect(spies.ignoreActions).not.toHaveBeenCalled();
    expect(refresh).toHaveBeenCalledOnce();
    expect(get(selected)).toEqual([]);
  });

  it('should skip the api and say why when nothing matches', async () => {
    const { ignore, refresh, selected } = setup([item('a', true)]);

    const status = await ignore(true); // all already ignored

    expect(status).toEqual({ message: expect.stringContaining('ignore.no_items.description'), success: false });
    expect(spies.ignoreActions).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
    expect(get(selected)).toHaveLength(1); // selection preserved
  });

  it('should hand the backend message back and keep the selection when the api throws', async () => {
    spies.ignoreActions.mockRejectedValue(new Error('boom'));
    const { ignore, refresh, selected } = setup([item('a')]);

    const status = await ignore(true);

    expect(refresh).not.toHaveBeenCalled();
    expect(get(selected)).toHaveLength(1);
    expect(status).toEqual({ message: 'boom', success: false });
  });

  it('should hand a failed toggle back to the caller', async () => {
    spies.unignoreActions.mockRejectedValue(new Error('boom'));
    const { toggle } = setup([]);

    expect(await toggle(item('y', true))).toEqual({ message: 'boom', success: false });
  });

  it('should toggle a single item based on its current state', async () => {
    const { toggle, selected } = setup([]);

    await toggle(item('x', false));
    expect(spies.ignoreActions).toHaveBeenCalledWith({ data: ['x'] });

    await toggle(item('y', true));
    expect(spies.unignoreActions).toHaveBeenCalledWith({ data: ['y'] });
    expect(get(selected)).toEqual([]);
  });

  it('should ignore or unignore a single item explicitly', async () => {
    const { ignoreSingle } = setup([]);

    await ignoreSingle(item('x', false), true);
    expect(spies.ignoreActions).toHaveBeenCalledWith({ data: ['x'] });

    await ignoreSingle(item('z', true), false);
    expect(spies.unignoreActions).toHaveBeenCalledWith({ data: ['z'] });
  });
});
