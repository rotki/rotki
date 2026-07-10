import type { Ref } from 'vue';
import type { LocationQuery } from '@/modules/core/table/route';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRememberTableFilter } from '@/modules/core/table/use-remember-table-filter';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';

const mockUserId = ref<string>('user1');
const mockReplace = vi.fn();

vi.mock('@/modules/auth/use-logged-user-identifier', () => ({
  useLoggedUserIdentifier: (): Ref<string> => mockUserId,
}));

vi.mock('vue-router', async importOriginal => ({
  ...await importOriginal<typeof import('vue-router')>(),
  useRouter: (): { replace: typeof mockReplace } => ({ replace: mockReplace }),
}));

const STORAGE_KEY = 'user1.rotki.table_filters';

interface Options {
  enabled?: boolean;
  history?: false | 'router' | 'external';
  query?: Ref<LocationQuery>;
}

function create(options: Options = {}): ReturnType<typeof useRememberTableFilter> {
  return useRememberTableFilter({
    enabled: ref(options.enabled ?? true),
    history: options.history ?? 'router',
    query: options.query ?? ref<LocationQuery>({}),
    tableId: ref(TableId.HISTORY),
  });
}

describe('useRememberTableFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    set(mockUserId, 'user1');
  });

  it('should not restore anything when disabled', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ [TableId.HISTORY]: { type: 'deposit' } }));
    const { restorePersistedFilter } = create({ enabled: false });
    await restorePersistedFilter();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('should replace the router query when history is router', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ [TableId.HISTORY]: { limit: '10', page: '2', type: 'deposit' } }));
    const { restorePersistedFilter } = create({ history: 'router' });
    await restorePersistedFilter();
    expect(mockReplace).toHaveBeenCalledWith({ query: { type: 'deposit' } });
  });

  it('should update the external query ref when history is external', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ [TableId.HISTORY]: { page: '2', type: 'withdrawal' } }));
    const query = ref<LocationQuery>({});
    const { restorePersistedFilter } = create({ history: 'external', query });
    await restorePersistedFilter();
    expect(get(query)).toEqual({ type: 'withdrawal' });
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('should do nothing when the saved filter is empty', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ [TableId.HISTORY]: {} }));
    const query = ref<LocationQuery>({});
    const { restorePersistedFilter } = create({ history: 'external', query });
    await restorePersistedFilter();
    expect(get(query)).toEqual({});
  });

  it('should persist a filter stripped of the limit param', async () => {
    const { savePersistedFilter } = create();
    savePersistedFilter({ limit: '25', page: '3', type: 'deposit' });
    await nextTick();
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored[TableId.HISTORY]).toEqual({ page: '3', type: 'deposit' });
  });

  it('should merge persisted filters across table ids', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ OTHER: { foo: 'bar' } }));
    const { savePersistedFilter } = create();
    savePersistedFilter({ type: 'deposit' });
    await nextTick();
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored.OTHER).toEqual({ foo: 'bar' });
    expect(stored[TableId.HISTORY]).toEqual({ type: 'deposit' });
  });
});
