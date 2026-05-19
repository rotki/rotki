import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NoteLocation } from '@/modules/core/common/notes';

const fetchUserNotes = vi.fn();
let location: ReturnType<typeof ref<string>>;

vi.mock('@/modules/notes/use-user-notes-api', () => ({
  useUserNotesApi: vi.fn().mockImplementation(() => ({ fetchUserNotes })),
}));

vi.mock('@/modules/notes/use-note-location', () => ({
  useNoteLocation: vi.fn().mockImplementation(() => location),
}));

// `useNotesCount` is a sharedComposable. Each test re-imports it with a fresh
// `location` ref so the previous instance's watchers don't leak.
async function freshUseNotesCount(initial: string): Promise<typeof import('@/modules/notes/use-notes-count').useNotesCount> {
  location = ref<string>(initial);
  vi.resetModules();
  const mod = await import('@/modules/notes/use-notes-count');
  return mod.useNotesCount;
}

describe('useNotesCount', () => {
  beforeEach(() => {
    fetchUserNotes.mockReset();
  });

  it('should fetch only the global count when no page location is set', async () => {
    fetchUserNotes.mockResolvedValue({ found: 7 });
    const useNotesCount = await freshUseNotesCount('');

    const { notesCount, globalNotesCount, hasSpecialNotes } = useNotesCount();
    await flushPromises();

    expect(fetchUserNotes).toHaveBeenCalledTimes(1);
    expect(fetchUserNotes).toHaveBeenCalledWith(expect.objectContaining({ location: NoteLocation.GLOBAL }));
    expect(get(notesCount)).toBe(0);
    expect(get(globalNotesCount)).toBe(7);
    expect(get(hasSpecialNotes)).toBe(false);
  });

  it('should fetch both page and global counts when location is set', async () => {
    fetchUserNotes
      .mockResolvedValueOnce({ found: 3 })
      .mockResolvedValueOnce({ found: 5 });
    const useNotesCount = await freshUseNotesCount(NoteLocation.DASHBOARD);

    const { notesCount, globalNotesCount, hasSpecialNotes } = useNotesCount();
    await flushPromises();

    expect(fetchUserNotes).toHaveBeenCalledTimes(2);
    expect(get(notesCount)).toBe(3);
    expect(get(globalNotesCount)).toBe(5);
    expect(get(hasSpecialNotes)).toBe(true);
  });

  it('should refetch when the location changes', async () => {
    fetchUserNotes.mockResolvedValue({ found: 0 });
    const useNotesCount = await freshUseNotesCount('');

    const { notesCount } = useNotesCount();
    await flushPromises();
    fetchUserNotes.mockClear();

    fetchUserNotes
      .mockResolvedValueOnce({ found: 11 })
      .mockResolvedValueOnce({ found: 2 });
    set(location, NoteLocation.DASHBOARD);
    await flushPromises();

    expect(get(notesCount)).toBe(11);
  });

  it('should return zero when fetchUserNotes throws', async () => {
    fetchUserNotes.mockRejectedValue(new Error('network'));
    const useNotesCount = await freshUseNotesCount('');

    const { notesCount, globalNotesCount } = useNotesCount();
    await flushPromises();

    expect(get(notesCount)).toBe(0);
    expect(get(globalNotesCount)).toBe(0);
  });
});
