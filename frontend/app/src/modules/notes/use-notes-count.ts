import type { ComputedRef, Ref } from 'vue';
import { createSharedComposable } from '@vueuse/core';
import { NoteLocation } from '@/modules/core/common/notes';
import { useNoteLocation } from '@/modules/notes/use-note-location';
import { useUserNotesApi } from '@/modules/notes/use-user-notes-api';

interface UseNotesCountReturn {
  globalNotesCount: Ref<number>;
  hasSpecialNotes: ComputedRef<boolean>;
  location: ComputedRef<string>;
  notesCount: Ref<number>;
  refresh: () => Promise<void>;
}

export const useNotesCount = createSharedComposable((): UseNotesCountReturn => {
  const location = useNoteLocation();
  const { fetchUserNotes } = useUserNotesApi();

  const notesCount = ref<number>(0);
  const globalNotesCount = ref<number>(0);

  const hasSpecialNotes = computed<boolean>(() => get(notesCount) > 0);

  async function fetchCount(locationValue: string): Promise<number> {
    try {
      const result = await fetchUserNotes({
        ascending: [false],
        limit: 1,
        location: locationValue,
        offset: 0,
        orderByAttributes: ['title'],
        titleSubstring: '',
      });
      return result.found;
    }
    catch {
      return 0;
    }
  }

  async function refresh(): Promise<void> {
    const locationValue = get(location);

    const [pageCount, globalCount] = await Promise.all([
      locationValue ? fetchCount(locationValue) : Promise.resolve(0),
      fetchCount(NoteLocation.GLOBAL),
    ]);

    set(notesCount, pageCount);
    set(globalNotesCount, globalCount);
  }

  watchImmediate(location, async () => {
    await refresh();
  });

  return {
    globalNotesCount,
    hasSpecialNotes,
    location,
    notesCount,
    refresh,
  };
});
