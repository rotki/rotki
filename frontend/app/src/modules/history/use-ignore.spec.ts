import type { Ref } from 'vue';
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
    showErrorMessage: vi.fn(),
  },
}));

vi.mock('@/modules/history/api/use-history-ignoring-api', () => ({
  useHistoryIgnoringApi: (): object => ({
    ignoreActions: spies.ignoreActions,
    unignoreActions: spies.unignoreActions,
  }),
}));

// Mocked outright rather than spread over `...actual`: importActual evaluates the real
// notifications graph, which costs ~1.2s to import.
// `getErrorMessage` is a pure helper re-exported from a light module, so take it from there.
vi.mock('@/modules/core/notifications/use-notifications', async () => ({
  getErrorMessage: (await vi.importActual<typeof import('@/modules/core/common/logging/error-handling')>(
    '@/modules/core/common/logging/error-handling',
  )).getErrorMessage,
  useNotifications: (): object => ({
    showErrorMessage: spies.showErrorMessage,
  }),
}));

function item(groupIdentifier: string, ignoredInAccounting = false): TestItem {
  return { groupIdentifier, ignoredInAccounting };
}

function setup(items: TestItem[]): {
  ignore: (ignored: boolean) => Promise<void>;
  ignoreSingle: (item: TestItem, ignored: boolean) => Promise<void>;
  toggle: (item: TestItem) => Promise<void>;
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

  it('should warn and skip the api when nothing matches', async () => {
    const { ignore, refresh, selected } = setup([item('a', true)]);

    await ignore(true); // all already ignored

    expect(spies.showErrorMessage).toHaveBeenCalledOnce();
    expect(spies.ignoreActions).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
    expect(get(selected)).toHaveLength(1); // selection preserved
  });

  it('should surface an error and keep the selection when the api throws', async () => {
    spies.ignoreActions.mockRejectedValue(new Error('boom'));
    const { ignore, refresh, selected } = setup([item('a')]);

    await ignore(true);

    expect(spies.showErrorMessage).toHaveBeenCalledOnce();
    expect(refresh).not.toHaveBeenCalled();
    expect(get(selected)).toHaveLength(1);
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
