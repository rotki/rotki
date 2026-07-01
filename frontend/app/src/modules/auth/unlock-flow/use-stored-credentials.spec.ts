import { none, some } from 'plainfp';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useStoredCredentials } from './use-stored-credentials';

const { getPassword, isPackagedRef, lastLoginRef, savedRememberPasswordRef } = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    getPassword: vi.fn(),
    isPackagedRef: vueRef(false),
    lastLoginRef: vueRef(''),
    savedRememberPasswordRef: vueRef(null),
  };
});

vi.mock('@/modules/auth/account-management', () => ({ lastLogin: lastLoginRef }));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => ({ getPassword, isPackaged: isPackagedRef.value })),
}));

vi.mock('@/modules/auth/use-remember-settings', () => ({
  useRememberSettings: vi.fn(() => ({ savedRememberPassword: savedRememberPasswordRef })),
}));

describe('useStoredCredentials', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(lastLoginRef, '');
    set(isPackagedRef, false);
    set(savedRememberPasswordRef, null);
  });

  it('should return none when there is no last login', async () => {
    const { resolveStoredCredentials } = useStoredCredentials();
    expect(await resolveStoredCredentials()).toEqual(none);
  });

  it('should return an empty password when not packaged', async () => {
    set(lastLoginRef, 'alice');
    set(isPackagedRef, false);

    const { resolveStoredCredentials } = useStoredCredentials();

    expect(await resolveStoredCredentials()).toEqual(some({ password: '', username: 'alice' }));
    expect(getPassword).not.toHaveBeenCalled();
  });

  it('should read the saved password when packaged and remember-password is on', async () => {
    set(lastLoginRef, 'alice');
    set(isPackagedRef, true);
    set(savedRememberPasswordRef, 'true');
    getPassword.mockResolvedValue('secret');

    const { resolveStoredCredentials } = useStoredCredentials();

    expect(await resolveStoredCredentials()).toEqual(some({ password: 'secret', username: 'alice' }));
    expect(getPassword).toHaveBeenCalledWith('alice');
  });

  it('should fall back to an empty password when the keychain has none', async () => {
    set(lastLoginRef, 'alice');
    set(isPackagedRef, true);
    set(savedRememberPasswordRef, 'true');
    getPassword.mockResolvedValue(undefined);

    const { resolveStoredCredentials } = useStoredCredentials();

    expect(await resolveStoredCredentials()).toEqual(some({ password: '', username: 'alice' }));
  });

  it('should not read the password when remember-password is off', async () => {
    set(lastLoginRef, 'alice');
    set(isPackagedRef, true);
    set(savedRememberPasswordRef, null);

    const { resolveStoredCredentials } = useStoredCredentials();

    expect(await resolveStoredCredentials()).toEqual(some({ password: '', username: 'alice' }));
    expect(getPassword).not.toHaveBeenCalled();
  });
});
