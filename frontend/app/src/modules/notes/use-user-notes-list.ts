import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { getCollectionData, setupEntryLimit } from '@/modules/core/common/data/collection-utils';
import { NoteLocation, type UserNote, type UserNoteDraft, type UserNotesRequestPayload } from '@/modules/core/common/notes';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useNotesCount } from '@/modules/notes/use-notes-count';
import { useUserNotesApi } from '@/modules/notes/use-user-notes-api';
import { usePremium } from '@/modules/premium/use-premium';

/** Notes fetched per page; each scroll to the bottom asks for one more page's worth. */
const PAGE_SIZE = 10;

/** How long typing settles before the list is filtered. */
const SEARCH_DEBOUNCE = 400;

function getDefaultForm(): UserNoteDraft {
  return {
    content: '',
    isPinned: false,
    location: NoteLocation.GLOBAL,
    title: '',
  };
}

interface UseUserNotesListOptions {
  /** Whether the list is scrolled to the bottom, which is what asks for the next page. */
  arrivedBottom: MaybeRefOrGetter<boolean>;
  /** The note location the list is scoped to. */
  location: MaybeRefOrGetter<string>;
  /** Two-way binding for the add/edit dialog. */
  open: Ref<boolean>;
}

interface UseUserNotesListReturn {
  /** Opens the dialog on a blank note. */
  addNote: () => void;
  /** Closes the delete confirmation without deleting. */
  clearDeleteDialog: () => void;
  /** Deletes the note the confirmation names, then refreshes the list and the badge count. */
  confirmDelete: () => Promise<void>;
  /** The notes on the current page. */
  data: ComputedRef<UserNote[]>;
  /** Arms the inline delete confirmation for one note. */
  deleteNote: (identifier: number) => void;
  /** Opens the dialog on an existing note. */
  editNote: (note: UserNote) => void;
  /** Whether the dialog is editing rather than creating. */
  editMode: Readonly<Ref<boolean>>;
  /** The note the delete confirmation is armed for, or null. */
  idToDelete: Readonly<Ref<number | null>>;
  /** The free-tier note cap. */
  limit: ComputedRef<number>;
  /** Fetches the first page, showing skeletons while it is in flight. */
  loadInitialNotes: () => Promise<void>;
  /** Whether the skeletons are showing. */
  loading: Readonly<Ref<boolean>>;
  /** The note the dialog is editing or creating. */
  modelForm: Ref<UserNoteDraft>;
  /** The search box contents. */
  modelSearch: Ref<string>;
  /**
   * Fixes a leaving row's box before it animates out.
   *
   * @remarks
   * The row is taken out of flow by the leave transition, so without this it collapses to zero
   * before it has faded. Anything that is not an element is left alone.
   */
  onBeforeLeave: (el: Element) => void;
  /** Clears the dialog's note and closes it. */
  resetForm: () => void;
  /** Refreshes the list and the badge count. */
  refreshNotes: () => Promise<void>;
  /** Whether the free-tier cap has been reached. */
  showUpgradeRow: ComputedRef<boolean>;
  /** Whether the inline delete confirmation is showing. */
  showDeleteConfirmation: Readonly<Ref<boolean>>;
  /** Pins or unpins a note. */
  togglePin: (note: UserNote) => Promise<void>;
}

/**
 * Drives the notes sidebar list: the search, the paging as it scrolls, the add/edit dialog and the
 * inline delete confirmation.
 *
 * @returns the list state and every action its rows offer
 */
export function useUserNotesList(options: UseUserNotesListOptions): UseUserNotesListReturn {
  const { arrivedBottom, location, open } = options;

  const modelSearch = shallowRef<string>('');
  const modelForm = ref<UserNoteDraft>(getDefaultForm());
  const titleSubstring = shallowRef<string>('');
  const showDeleteConfirmation = shallowRef<boolean>(false);
  const idToDelete = shallowRef<number | null>(null);
  const editMode = shallowRef<boolean>(false);
  const loading = shallowRef<boolean>(false);
  const page = shallowRef<number>(1);
  const nextPageDisabled = shallowRef<boolean>(true);
  const atBottom = shallowRef<boolean>(false);

  const { deleteUserNote, fetchUserNotes, updateUserNote } = useUserNotesApi();
  const { refresh: refreshNotesCount } = useNotesCount();
  const premium = usePremium();
  const { logged } = storeToRefs(useSessionAuthStore());

  const extraParams = computed(() => ({
    location: toValue(location),
    titleSubstring: get(titleSubstring),
  }));

  const { collection: notes, pagination, refetch } = useServerTable<UserNote, UserNotesRequestPayload>({
    fetch: fetchUserNotes,
    params: [{ to: 'both', values: extraParams }],
    sort: {
      default: [{
        column: 'isPinned',
        direction: 'desc',
      }, {
        column: 'lastUpdateTimestamp',
        direction: 'desc',
      }],
    },
  });

  const { data, found, limit, total } = getCollectionData<UserNote>(notes);
  const { showUpgradeRow } = setupEntryLimit(limit, found, total);

  async function fetchNotes(): Promise<void> {
    await refetch();
    set(loading, false);
  }

  async function loadInitialNotes(): Promise<void> {
    set(loading, true);
    await fetchNotes();
  }

  async function refreshNotes(): Promise<void> {
    await fetchNotes();
    await refreshNotesCount();
  }

  async function callUpdateNote(payload: Partial<UserNote>): Promise<void> {
    await updateUserNote(payload);
    await refreshNotes();
  }

  async function togglePin(note: UserNote): Promise<void> {
    await callUpdateNote({
      ...note,
      isPinned: !note.isPinned,
    });
  }

  function resetForm(): void {
    set(editMode, false);
    set(modelForm, getDefaultForm());
    set(open, false);
  }

  function addNote(): void {
    resetForm();
    set(open, true);
  }

  function editNote(note: UserNote): void {
    set(editMode, true);
    set(modelForm, { ...note });
    set(open, true);
  }

  function deleteNote(identifier: number): void {
    set(showDeleteConfirmation, true);
    set(idToDelete, identifier);
  }

  function clearDeleteDialog(): void {
    set(showDeleteConfirmation, false);
    set(idToDelete, null);
  }

  async function confirmDelete(): Promise<void> {
    const id = get(idToDelete);
    if (id === null)
      return;

    await deleteUserNote(id);
    clearDeleteDialog();
    await refreshNotes();
  }

  function onBeforeLeave(el: Element): void {
    if (!(el instanceof HTMLElement))
      return;

    el.style.height = `${el.offsetHeight}px`;
    el.style.width = `${el.offsetWidth}px`;
  }

  async function refetchOnPremiumChange(): Promise<void> {
    if (get(logged))
      await fetchNotes();
  }

  watch(page, (page) => {
    set(pagination, {
      ...get(pagination),
      limit: PAGE_SIZE * page,
      page: 1,
    });
  });

  watch(premium, refetchOnPremiumChange);

  watchDebounced(modelSearch, (search) => {
    set(titleSubstring, search);
  }, { debounce: SEARCH_DEBOUNCE });

  watch(notes, (notes) => {
    set(nextPageDisabled, notes.data.length >= notes.found);
  });

  watch(() => toValue(arrivedBottom), (arrived) => {
    set(atBottom, arrived && get(data).length > 0);
  });

  const shouldIncreasePage = logicAnd(atBottom, logicNot(nextPageDisabled));

  watch(shouldIncreasePage, (increasePage) => {
    if (increasePage)
      set(page, get(page) + 1);
  });

  return {
    addNote,
    clearDeleteDialog,
    confirmDelete,
    data,
    deleteNote,
    editMode: readonly(editMode),
    editNote,
    idToDelete: readonly(idToDelete),
    limit,
    loadInitialNotes,
    loading: readonly(loading),
    modelForm,
    modelSearch,
    onBeforeLeave,
    refreshNotes,
    resetForm,
    showDeleteConfirmation: readonly(showDeleteConfirmation),
    showUpgradeRow,
    togglePin,
  };
}
