import type { Collection } from '@/modules/core/common/collection';
import type { UserNote } from '@/modules/core/common/notes';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import UserNotesList from '@/modules/notes/UserNotesList.vue';

interface TableState {
  collection?: Ref<Collection<UserNote>>;
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

async function createWrapper(data: UserNote[] = []): Promise<VueWrapper> {
  notes = ref<Collection<UserNote>>(collection(data));
  tableState.collection = notes;
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
