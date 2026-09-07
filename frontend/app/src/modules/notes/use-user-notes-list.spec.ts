import type { Collection } from '@/modules/core/common/collection';
import type { UserNote } from '@/modules/core/common/notes';
import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComputedRef, effectScope, type Ref, ref } from 'vue';
import { useUserNotesList } from './use-user-notes-list';

interface NoteFilterParams {
  location: string;
  titleSubstring: string;
}

interface CapturedTableOptions {
  params: { to: string; values: ComputedRef<NoteFilterParams> }[];
  sort: { default: { column: string; direction: string }[] };
}

interface TableState {
  collection?: Ref<Collection<UserNote>>;
  options?: CapturedTableOptions;
  pagination?: Ref<{ limit: number; page: number }>;
}

let premium: Ref<boolean>;
let logged: Ref<boolean>;
let notes: Ref<Collection<UserNote>>;
let pagination: Ref<{ limit: number; page: number }>;
let open: Ref<boolean>;
let arrivedBottom: Ref<boolean>;
let scope: ReturnType<typeof effectScope>;

const {
  deleteUserNote,
  fetchUserNotes,
  refreshNotesCount,
  refetch,
  tableState,
  updateUserNote,
} = vi.hoisted(() => {
  const tableState: TableState = {};
  return {
    deleteUserNote: vi.fn(async () => Promise.resolve(true)),
    fetchUserNotes: vi.fn(),
    refetch: vi.fn(async () => Promise.resolve()),
    refreshNotesCount: vi.fn(async () => Promise.resolve()),
    tableState,
    updateUserNote: vi.fn(async () => Promise.resolve(true)),
  };
});

vi.mock('@/modules/notes/use-user-notes-api', () => ({
  useUserNotesApi: (): Record<string, unknown> => ({
    deleteUserNote,
    fetchUserNotes,
    updateUserNote,
  }),
}));

vi.mock('@/modules/notes/use-notes-count', () => ({
  useNotesCount: (): Record<string, unknown> => ({ refresh: refreshNotesCount }),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: (options: CapturedTableOptions): Record<string, unknown> => {
    tableState.options = options;
    return {
      collection: tableState.collection,
      pagination: tableState.pagination,
      refetch,
    };
  },
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

function collection(data: UserNote[], found = data.length): Collection<UserNote> {
  return {
    data,
    found,
    limit: -1,
    total: found,
    totalValue: undefined,
  };
}

/** The query the list hands the table, as captured from the stubbed `useServerTable`. */
function filterParams(): ComputedRef<NoteFilterParams> {
  assert(tableState.options);
  return tableState.options.params[0].values;
}

function list(): ReturnType<typeof useUserNotesList> {
  scope = effectScope();
  return scope.run(() => useUserNotesList({ arrivedBottom, location: 'G', open }))!;
}

describe('modules/notes/useUserNotesList', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    premium = ref<boolean>(false);
    logged = ref<boolean>(true);
    notes = ref<Collection<UserNote>>(collection([]));
    pagination = ref({ limit: 10, page: 1 });
    open = ref<boolean>(false);
    arrivedBottom = ref<boolean>(false);
    tableState.collection = notes;
    tableState.pagination = pagination;
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('loading the list', () => {
    it('should show skeletons while the first page is in flight', async () => {
      const { loadInitialNotes, loading } = list();

      const pending = loadInitialNotes();
      expect(get(loading)).toBe(true);

      await pending;
      expect(get(loading)).toBe(false);
      expect(refetch).toHaveBeenCalledOnce();
    });

    it('should refetch when premium changes while logged in', async () => {
      list();

      set(premium, true);
      await flushPromises();

      expect(refetch).toHaveBeenCalledOnce();
    });

    it('should not refetch on a premium change while logged out', async () => {
      set(logged, false);
      list();

      set(premium, true);
      await flushPromises();

      expect(refetch).not.toHaveBeenCalled();
    });
  });

  describe('the search box', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should not filter on every keystroke', async () => {
      const { modelSearch } = list();

      set(modelSearch, 'gro');
      await vi.advanceTimersByTimeAsync(200);
      set(modelSearch, 'groceries');
      await vi.advanceTimersByTimeAsync(200);

      expect(refetch).not.toHaveBeenCalled();
    });

    it('should filter once typing settles', async () => {
      const { modelSearch } = list();

      set(modelSearch, 'groceries');
      await vi.advanceTimersByTimeAsync(400);

      expect(get(filterParams())).toEqual({ location: 'G', titleSubstring: 'groceries' });
    });

    it('should not narrow the query while typing is still settling', async () => {
      const { modelSearch } = list();

      set(modelSearch, 'gro');
      await vi.advanceTimersByTimeAsync(200);

      expect(get(filterParams()).titleSubstring).toBe('');
    });
  });

  describe('the add and edit dialog', () => {
    it('should open a blank note to add', () => {
      const { addNote, editMode, modelForm } = list();
      addNote();

      expect(get(open)).toBe(true);
      expect(get(editMode)).toBe(false);
      expect(get(modelForm)).toEqual({ content: '', isPinned: false, location: 'G', title: '' });
    });

    it('should open an existing note to edit', () => {
      const existing = note({ identifier: 4, title: 'shopping' });

      const { editMode, editNote, modelForm } = list();
      editNote(existing);

      expect(get(open)).toBe(true);
      expect(get(editMode)).toBe(true);
      expect(get(modelForm)).toEqual(existing);
    });

    it('should not hand the dialog the caller\'s own note object', () => {
      const existing = note({ title: 'shopping' });

      const { editNote, modelForm } = list();
      editNote(existing);
      get(modelForm).title = 'edited in the dialog';

      expect(existing.title).toBe('shopping');
    });

    it('should blank the note and close the dialog on reset', () => {
      const { editNote, modelForm, resetForm } = list();
      editNote(note({ title: 'shopping' }));
      resetForm();

      expect(get(open)).toBe(false);
      expect(get(modelForm).title).toBe('');
    });
  });

  describe('pinning', () => {
    it('should pin an unpinned note and refresh the list and the count', async () => {
      const { togglePin } = list();
      await togglePin(note({ identifier: 3, isPinned: false }));

      expect(updateUserNote).toHaveBeenCalledWith(expect.objectContaining({ identifier: 3, isPinned: true }));
      expect(refetch).toHaveBeenCalledOnce();
      expect(refreshNotesCount).toHaveBeenCalledOnce();
    });

    it('should unpin a pinned note', async () => {
      const { togglePin } = list();
      await togglePin(note({ identifier: 3, isPinned: true }));

      expect(updateUserNote).toHaveBeenCalledWith(expect.objectContaining({ identifier: 3, isPinned: false }));
    });
  });

  describe('deleting a note', () => {
    it('should delete nothing until the confirmation is answered', () => {
      const { deleteNote, idToDelete, showDeleteConfirmation } = list();
      deleteNote(7);

      expect(get(showDeleteConfirmation)).toBe(true);
      expect(get(idToDelete)).toBe(7);
      expect(deleteUserNote).not.toHaveBeenCalled();
    });

    it('should delete exactly the note the confirmation names', async () => {
      const { confirmDelete, deleteNote } = list();
      deleteNote(7);
      await confirmDelete();

      expect(deleteUserNote).toHaveBeenCalledWith(7);
      expect(deleteUserNote).toHaveBeenCalledOnce();
    });

    it('should close the confirmation and refresh after deleting', async () => {
      const { confirmDelete, deleteNote, idToDelete, showDeleteConfirmation } = list();
      deleteNote(7);
      await confirmDelete();

      expect(get(showDeleteConfirmation)).toBe(false);
      expect(get(idToDelete)).toBeNull();
      expect(refreshNotesCount).toHaveBeenCalledOnce();
    });

    it('should delete nothing when the confirmation is cancelled', () => {
      const { clearDeleteDialog, deleteNote, idToDelete, showDeleteConfirmation } = list();
      deleteNote(7);
      clearDeleteDialog();

      expect(get(showDeleteConfirmation)).toBe(false);
      expect(get(idToDelete)).toBeNull();
      expect(deleteUserNote).not.toHaveBeenCalled();
    });

    it('should delete nothing when confirmed with no note armed', async () => {
      const { confirmDelete } = list();
      await confirmDelete();

      expect(deleteUserNote).not.toHaveBeenCalled();
      expect(refetch).not.toHaveBeenCalled();
    });
  });

  describe('paging as it scrolls', () => {
    it('should ask for another page at the bottom while more remain', async () => {
      list();
      set(notes, collection([note({ identifier: 1 })], 30));
      await flushPromises();

      set(arrivedBottom, true);
      await flushPromises();

      expect(get(pagination).limit).toBe(20);
    });

    it('should not page past the end of the list', async () => {
      list();
      set(notes, collection([note({ identifier: 1 })], 1));
      await flushPromises();

      set(arrivedBottom, true);
      await flushPromises();

      expect(get(pagination).limit).toBe(10);
    });

    it('should not page an empty list', async () => {
      list();
      set(notes, collection([], 0));
      await flushPromises();

      set(arrivedBottom, true);
      await flushPromises();

      expect(get(pagination).limit).toBe(10);
    });

    it('should keep paging while the user stays at the bottom', async () => {
      list();
      set(notes, collection([note({ identifier: 1 })], 30));
      await flushPromises();

      set(arrivedBottom, true);
      await flushPromises();
      set(arrivedBottom, false);
      await flushPromises();
      set(arrivedBottom, true);
      await flushPromises();

      expect(get(pagination).limit).toBe(30);
    });
  });

  describe('the leave transition', () => {
    it('should pin the row box before it animates out', () => {
      const el = document.createElement('div');
      Object.defineProperty(el, 'offsetHeight', { value: 48 });
      Object.defineProperty(el, 'offsetWidth', { value: 300 });

      const { onBeforeLeave } = list();
      onBeforeLeave(el);

      expect(el.style.height).toBe('48px');
      expect(el.style.width).toBe('300px');
    });

    it('should leave anything that is not an element alone', () => {
      const el = document.createElementNS('http://www.w3.org/2000/svg', 'svg');

      const { onBeforeLeave } = list();

      expect(() => onBeforeLeave(el)).not.toThrow();
    });
  });
});
