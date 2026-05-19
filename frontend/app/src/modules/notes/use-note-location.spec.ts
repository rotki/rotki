import { describe, expect, it, vi } from 'vitest';
import { useNoteLocation } from '@/modules/notes/use-note-location';

const { useRouteMock } = vi.hoisted(() => ({
  useRouteMock: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: useRouteMock,
}));

function mockRoute(meta: Record<string, unknown>, matched: { meta: Record<string, unknown> }[] = []): void {
  useRouteMock.mockReturnValueOnce({ matched, meta });
}

describe('useNoteLocation', () => {
  it('should return noteLocation from current route meta when present', () => {
    mockRoute({ noteLocation: 'dashboard' });

    const location = useNoteLocation();
    expect(get(location)).toBe('dashboard');
  });

  it('should fall back to noteLocation from matched routes when meta lacks one', () => {
    mockRoute({}, [
      { meta: {} },
      { meta: { noteLocation: 'parent-section' } },
    ]);

    const location = useNoteLocation();
    expect(get(location)).toBe('parent-section');
  });

  it('should prefer the last matched route when multiple ancestors define noteLocation', () => {
    mockRoute({}, [
      { meta: { noteLocation: 'outer' } },
      { meta: { noteLocation: 'inner' } },
    ]);

    const location = useNoteLocation();
    expect(get(location)).toBe('inner');
  });

  it('should return empty string when no noteLocation is defined', () => {
    mockRoute({}, [{ meta: {} }]);

    const location = useNoteLocation();
    expect(get(location)).toBe('');
  });

  it('should coerce non-string noteLocation values to string', () => {
    mockRoute({ noteLocation: 42 });

    const location = useNoteLocation();
    expect(get(location)).toBe('42');
  });
});
