import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLoginRememberOptions } from './use-login-remember-options';

const { clearPassword, interop, storePassword } = vi.hoisted(() => ({
  clearPassword: vi.fn(),
  interop: { isPackaged: false },
  storePassword: vi.fn(),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): Record<string, unknown> => ({
    clearPassword,
    get isPackaged() {
      return interop.isPackaged;
    },
    storePassword,
  }),
}));

describe('modules/auth/login/useLoginRememberOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    interop.isPackaged = false;
  });

  it('should default remember-username to true when not running on docker', () => {
    const { loadRememberSettings, modelRememberUsername } = useLoginRememberOptions({ isDocker: false });

    loadRememberSettings();

    expect(get(modelRememberUsername)).toBe(true);
  });

  it('should default remember-username to false on docker with nothing persisted', () => {
    const { loadRememberSettings, modelRememberUsername } = useLoginRememberOptions({ isDocker: true });

    loadRememberSettings();

    expect(get(modelRememberUsername)).toBe(false);
  });

  it('should restore remember-username on docker when it was persisted', () => {
    localStorage.setItem('rotki.remember_username', 'true');
    const { loadRememberSettings, modelRememberUsername } = useLoginRememberOptions({ isDocker: true });

    loadRememberSettings();

    expect(get(modelRememberUsername)).toBe(true);
  });

  it('should restore remember-password from persisted settings', () => {
    localStorage.setItem('rotki.remember_password', 'true');
    const { loadRememberSettings, modelRememberPassword } = useLoginRememberOptions({ isDocker: false });

    loadRememberSettings();

    expect(get(modelRememberPassword)).toBe(true);
  });

  it('should persist the flag when remember-username is enabled', async () => {
    const { modelRememberUsername } = useLoginRememberOptions({ isDocker: true });

    set(modelRememberUsername, true);
    await nextTick();

    expect(localStorage.getItem('rotki.remember_username')).toBe('true');
  });

  it('should drop the stored username when remember-username is disabled', async () => {
    localStorage.setItem('rotki.remember_username', 'true');
    localStorage.setItem('rotki.username', 'alice');
    const { modelRememberUsername } = useLoginRememberOptions({ isDocker: true });

    set(modelRememberUsername, true);
    await nextTick();
    set(modelRememberUsername, false);
    await nextTick();

    expect(localStorage.getItem('rotki.remember_username')).toBeNull();
  });

  it('should clear the stored password when remember-password is disabled on a packaged build', async () => {
    interop.isPackaged = true;
    const { modelRememberPassword } = useLoginRememberOptions({ isDocker: false });

    set(modelRememberPassword, true);
    await nextTick();
    set(modelRememberPassword, false);
    await nextTick();

    expect(clearPassword).toHaveBeenCalledTimes(1);
  });

  it('should not touch the stored password on a non-packaged build', async () => {
    const { modelRememberPassword } = useLoginRememberOptions({ isDocker: false });

    set(modelRememberPassword, true);
    await nextTick();
    set(modelRememberPassword, false);
    await nextTick();

    expect(clearPassword).not.toHaveBeenCalled();
  });

  it('should store the username on login when remember-username is on', async () => {
    const { modelRememberUsername, rememberCredentials } = useLoginRememberOptions({ isDocker: true });

    set(modelRememberUsername, true);
    await nextTick();
    await rememberCredentials('alice', 'secret');

    expect(localStorage.getItem('rotki.username')).toBe('alice');
  });

  it('should not store the username on login when remember-username is off', async () => {
    const { modelRememberUsername, rememberCredentials } = useLoginRememberOptions({ isDocker: true });

    set(modelRememberUsername, false);
    await nextTick();
    await rememberCredentials('alice', 'secret');

    // useLocalStorage writes its '' default on init, so the key exists but stays empty
    expect(localStorage.getItem('rotki.username')).toBe('');
  });

  it('should store the password on login only on a packaged build', async () => {
    interop.isPackaged = true;
    const { modelRememberPassword, rememberCredentials } = useLoginRememberOptions({ isDocker: false });

    set(modelRememberPassword, true);
    await nextTick();
    await rememberCredentials('alice', 'secret');

    expect(storePassword).toHaveBeenCalledWith('alice', 'secret');
  });

  it('should not store the password when remember-password is off', async () => {
    interop.isPackaged = true;
    const { modelRememberPassword, rememberCredentials } = useLoginRememberOptions({ isDocker: false });

    set(modelRememberPassword, false);
    await nextTick();
    await rememberCredentials('alice', 'secret');

    expect(storePassword).not.toHaveBeenCalled();
  });

  it('should expose the persisted username so the form can suppress the initial touched emit', () => {
    localStorage.setItem('rotki.username', 'alice');
    const { storedUsername } = useLoginRememberOptions({ isDocker: false });

    expect(get(storedUsername)).toBe('alice');
  });
});
