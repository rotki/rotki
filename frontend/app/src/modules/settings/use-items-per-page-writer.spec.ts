import type { EffectScope } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { endSession, finishPendingWrites } from '@/modules/core/session/session-lifecycle';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useItemsPerPageWriter } from '@/modules/settings/use-items-per-page-writer';

const { mockPatchFrontendSettings } = vi.hoisted(() => ({ mockPatchFrontendSettings: vi.fn() }));

vi.mock('@/modules/settings/api/use-settings-api', () => ({
  useSettingsApi: vi.fn(() => ({ patchFrontendSettings: mockPatchFrontendSettings })),
}));

/** Matches PERSIST_MAX_WAIT_MS in use-items-per-page-writer.ts, the longest a write can wait. */
const MAX_WAIT_MS = 1200;

describe('useItemsPerPageWriter', () => {
  let scopes: EffectScope[];

  function startWriter(): void {
    const scope = effectScope();
    scope.run(() => useItemsPerPageWriter());
    scopes.push(scope);
  }

  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    useSettingsRepo();
    set(useItemsPerPage(), 10);
    mockPatchFrontendSettings.mockReset().mockResolvedValue(undefined);
    scopes = [];
  });

  afterEach(() => {
    for (const scope of scopes)
      scope.stop();
    vi.useRealTimers();
  });

  it('should persist a table\'s rows-per-page choice once the debounce settles', async () => {
    startWriter();

    set(useItemsPerPage(), 25);
    await vi.advanceTimersByTimeAsync(MAX_WAIT_MS);

    expect(mockPatchFrontendSettings).toHaveBeenCalledExactlyOnceWith({ itemsPerPage: 25 });
  });

  it('should not write back the stored value the repo pushes at login', async () => {
    startWriter();

    useSettingsRepo().updateFrontend({ itemsPerPage: 50 });
    await vi.advanceTimersByTimeAsync(MAX_WAIT_MS);

    expect(get(useItemsPerPage())).toBe(50);
    expect(mockPatchFrontendSettings).not.toHaveBeenCalled();
  });

  it('should write a choice once however many callers use the writer, while the backend is slow', async () => {
    let finishWrite: ((value: undefined) => void) | undefined;
    mockPatchFrontendSettings.mockReturnValue(new Promise((resolve) => {
      finishWrite = resolve;
    }));
    startWriter();
    startWriter();
    startWriter();

    set(useItemsPerPage(), 25);
    await vi.advanceTimersByTimeAsync(MAX_WAIT_MS);
    finishWrite?.(undefined);
    await vi.advanceTimersByTimeAsync(0);

    expect(mockPatchFrontendSettings).toHaveBeenCalledOnce();
  });

  it('should write a pending choice when the logout finishes pending writes, and not again', async () => {
    startWriter();

    set(useItemsPerPage(), 25);
    await finishPendingWrites();
    expect(mockPatchFrontendSettings).toHaveBeenCalledExactlyOnceWith({ itemsPerPage: 25 });

    await vi.advanceTimersByTimeAsync(MAX_WAIT_MS);
    expect(mockPatchFrontendSettings).toHaveBeenCalledOnce();
  });

  it('should drop a write still scheduled when the session ends', async () => {
    startWriter();

    set(useItemsPerPage(), 25);
    endSession();
    await vi.advanceTimersByTimeAsync(MAX_WAIT_MS);

    expect(mockPatchFrontendSettings).not.toHaveBeenCalled();
  });
});
