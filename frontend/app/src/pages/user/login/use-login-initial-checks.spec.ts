import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLoginInitialChecks } from './use-login-initial-checks';

const { checkForUpdate, interopState } = vi.hoisted(() => ({
  checkForUpdate: vi.fn().mockResolvedValue(undefined),
  interopState: { isPackaged: false },
}));

vi.mock('@/modules/session/use-update-checker', () => ({
  useUpdateChecker: vi.fn(() => ({ checkForUpdate })),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => ({ isPackaged: interopState.isPackaged })),
}));

describe('pages/user/login/useLoginInitialChecks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    interopState.isPackaged = false;
  });

  it('should run the packaged app-update check on Electron', async () => {
    interopState.isPackaged = true;

    await useLoginInitialChecks().performInitialChecks();

    expect(checkForUpdate).toHaveBeenCalled();
  });

  it('should fire no pre-login checks on web (fix #2: no gated calls before login)', async () => {
    await useLoginInitialChecks().performInitialChecks();

    expect(checkForUpdate).not.toHaveBeenCalled();
  });
});
