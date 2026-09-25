import type { Collection } from '@/modules/core/common/collection';
import type { UserNote } from '@/modules/core/common/notes';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref, shallowRef } from 'vue';
import { RequestFailed, type RequestFailure } from '@/modules/core/api/request-result';
import UserNotesList from '@/modules/notes/UserNotesList.vue';

interface TableState {
  collection?: Ref<Collection<UserNote>>;
  error?: Ref<RequestFailure | undefined>;
  pagination?: Ref<{ limit: number; page: number }>;
}

let premium: Ref<boolean>;
let logged: Ref<boolean>;
let notes: Ref<Collection<UserNote>>;

const {
  deleteUserNote,
  refetch,
  refreshNotesCount,
  tableState,
  updateUserNote,
} = vi.hoisted(() => {
  const tableState: TableState = {};
  return {
    deleteUserNote: vi.fn(async () => Promise.resolve(true)),
    refetch: vi.fn(async () => Promise.resolve()),
    refreshNotesCount: vi.fn(async () => Promise.resolve()),
    tableState,
    updateUserNote: vi.fn(async () => Promise.resolve(true)),
  };
});

vi.mock('@/modules/notes/use-user-notes-api', () => ({
  useUserNotesApi: (): Record<string, unknown> => ({
    deleteUserNote,
    fetchUserNotes: vi.fn(),
    updateUserNote,
  }),
}));

vi.mock('@/modules/notes/use-notes-count', () => ({
  useNotesCount: (): Record<string, unknown> => ({ refresh: refreshNotesCount }),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: (): Record<string, unknown> => ({
    collection: tableState.collection,
    error: tableState.error,
    pagination: tableState.pagination,
    refetch,
  }),
}));

vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: (): Ref<boolean> => premium,
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): Record<string, unknown> => ({ logged }),
}));

function note(overrides: Partial<UserNote> = {}): UserNote {
  return {
    content: 'the content',
    identifier: 1,
    isPinned: false,
    lastUpdateTimestamp: 1_700_000_000,
    location: 'G',
    title: 'the title',
    ...overrides,
  };
}

function collection(data: UserNote[]): Collection<UserNote> {
  return { data, found: data.length, limit: -1, total: data.length, totalValue: undefined };
}

async function createWrapper(data: UserNote[] = [], failure?: RequestFailure): Promise<VueWrapper> {
  notes = ref<Collection<UserNote>>(collection(data));
  tableState.collection = notes;
  tableState.error = shallowRef<RequestFailure | undefined>(failure);
  tableState.pagination = ref({ limit: 10, page: 1 });

  const wrapper = mount(UserNotesList, {
    global: { stubs: { DateDisplay: true, ExternalLink: true, UserNotesFormDialog: true } },
    props: { open: false },
  });
  await flushPromises();
  return wrapper;
}

describe('modules/notes/UserNotesList.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    premium = ref<boolean>(true);
    logged = ref<boolean>(true);
  });

  it('should fetch the first page when it opens', async () => {
    await createWrapper();

    expect(refetch).toHaveBeenCalledOnce();
  });

  it('should render one card per note', async () => {
    const wrapper = await createWrapper([note({ identifier: 1 }), note({ identifier: 2 })]);

    expect(wrapper.findAll('[data-testid=note-card]')).toHaveLength(2);
  });

  it('should say so when there are no notes', async () => {
    const wrapper = await createWrapper();

    expect(wrapper.text()).toContain('notes_menu.empty_notes');
    expect(wrapper.find('[data-testid=notes-fetch-error]').exists()).toBe(false);
  });

  describe('when the notes could not be loaded', () => {
    const failure = RequestFailed({ cause: undefined, message: 'backend is down' });

    it('should name the failure instead of claiming there are no notes', async () => {
      const wrapper = await createWrapper([], failure);

      expect(wrapper.find('[data-testid=notes-fetch-error]').text()).toContain('backend is down');
      expect(wrapper.text()).not.toContain('notes_menu.empty_notes');
    });

    it('should keep the notes it already shows beside the failure', async () => {
      const wrapper = await createWrapper([note({ identifier: 1 })], failure);

      expect(wrapper.find('[data-testid=notes-fetch-error]').exists()).toBe(true);
      expect(wrapper.findAll('[data-testid=note-card]')).toHaveLength(1);
    });

    it('should load the notes again from the retry', async () => {
      const wrapper = await createWrapper([], failure);
      refetch.mockClear();

      await wrapper.find('[data-testid=notes-retry]').trigger('click');
      await flushPromises();

      expect(refetch).toHaveBeenCalledOnce();
    });
  });

  it('should open the dialog to add a note', async () => {
    const wrapper = await createWrapper();

    await wrapper.find('[data-testid=notes-add]').trigger('click');

    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([true]);
  });

  it('should pin the note whose pin was pressed', async () => {
    const wrapper = await createWrapper([
      note({ identifier: 1, title: 'first' }),
      note({ identifier: 2, title: 'second' }),
    ]);

    const cards = wrapper.findAll('[data-testid=note-card]');
    const second = cards.find(card => card.text().includes('second'))!;
    await second.find('[data-testid=note-pin]').trigger('click');

    expect(updateUserNote).toHaveBeenCalledWith(expect.objectContaining({ identifier: 2, isPinned: true }));
  });

  it('should ask before deleting, and delete nothing until confirmed', async () => {
    const wrapper = await createWrapper([note({ identifier: 5 })]);

    await wrapper.find('[data-testid=note-delete]').trigger('click');

    expect(wrapper.text()).toContain('notes_menu.delete_confirmation');
    expect(deleteUserNote).not.toHaveBeenCalled();
  });

  it('should delete the confirmed note', async () => {
    const wrapper = await createWrapper([note({ identifier: 5 })]);

    await wrapper.find('[data-testid=note-delete]').trigger('click');
    await wrapper.find('[data-testid=note-delete-confirm]').trigger('click');

    expect(deleteUserNote).toHaveBeenCalledWith(5);
  });

  it('should delete nothing when the confirmation is dismissed', async () => {
    const wrapper = await createWrapper([note({ identifier: 5 })]);

    await wrapper.find('[data-testid=note-delete]').trigger('click');
    await wrapper.find('[data-testid=note-delete-cancel]').trigger('click');

    expect(wrapper.text()).not.toContain('notes_menu.delete_confirmation');
    expect(deleteUserNote).not.toHaveBeenCalled();
  });

  it('should confirm against only the note whose delete was pressed', async () => {
    const wrapper = await createWrapper([
      note({ identifier: 1, title: 'first' }),
      note({ identifier: 2, title: 'second' }),
    ]);

    const cards = wrapper.findAll('[data-testid=note-card]');
    const second = cards.find(card => card.text().includes('second'))!;
    await second.find('[data-testid=note-delete]').trigger('click');

    expect(wrapper.findAll('[data-testid=note-delete-confirm]')).toHaveLength(1);
    expect(second.text()).toContain('notes_menu.delete_confirmation');
  });
});
