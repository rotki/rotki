import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const checkForUpdates = vi.fn();

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): ReturnType<typeof useInterop> => createMock<ReturnType<typeof useInterop>>({ checkForUpdates }),
}));

async function loadComposable(): Promise<typeof import('./use-update-checker')['useUpdateChecker']> {
  vi.resetModules();
  return (await import('./use-update-checker')).useUpdateChecker;
}

describe('useUpdateChecker', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    localStorage.clear();
    // showUpdatePopup is backed by useSessionStorage, so sessionStorage must be
    // cleared too or a prior test's `true` leaks into the default-false test.
    sessionStorage.clear();
  });

  it('should default the update popup to false', async () => {
    const useUpdateChecker = await loadComposable();
    const { showUpdatePopup } = useUpdateChecker();
    expect(get(showUpdatePopup)).toBe(false);
  });

  it('should flag the popup when an update is available', async () => {
    checkForUpdates.mockResolvedValue(true);
    const useUpdateChecker = await loadComposable();
    const { checkForUpdate, showUpdatePopup } = useUpdateChecker();
    await checkForUpdate();
    expect(checkForUpdates).toHaveBeenCalledOnce();
    expect(get(showUpdatePopup)).toBe(true);
  });

  it('should keep the popup hidden when no update is available', async () => {
    checkForUpdates.mockResolvedValue(false);
    const useUpdateChecker = await loadComposable();
    const { checkForUpdate, showUpdatePopup } = useUpdateChecker();
    await checkForUpdate();
    expect(get(showUpdatePopup)).toBe(false);
  });
});
