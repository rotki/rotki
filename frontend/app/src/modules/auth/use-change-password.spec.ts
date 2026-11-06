import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useChangePassword } from '@/modules/auth/use-change-password';

const spies = vi.hoisted(() => ({
  changeUserPassword: vi.fn<(username: string, current: string, next: string) => Promise<boolean>>(),
  clearPassword: vi.fn<() => Promise<void>>(),
  colibriLogin: vi.fn<(payload: object) => Promise<void>>(),
  colibriLogout: vi.fn<() => Promise<void>>(),
}));

vi.mock('@/modules/auth/use-users-api', () => ({
  useUsersApi: (): object => ({
    changeUserPassword: spies.changeUserPassword,
    colibriLogin: spies.colibriLogin,
    colibriLogout: spies.colibriLogout,
  }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): object => ({ clearPassword: spies.clearPassword, isPackaged: false }),
}));

const PAYLOAD = { currentPassword: 'old', newPassword: 'new' };

describe('useChangePassword', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    spies.colibriLogin.mockResolvedValue(undefined);
    spies.colibriLogout.mockResolvedValue(undefined);
  });

  it('should report a change that went through, re-authenticating colibri with the new password', async () => {
    spies.changeUserPassword.mockResolvedValue(true);

    const status = await useChangePassword().changePassword(PAYLOAD);
    await flushPromises();

    expect(status).toEqual({ success: true });
    expect(spies.colibriLogin).toHaveBeenCalledWith(expect.objectContaining({ password: 'new' }));
  });

  it('should hand a change the backend refused back with a reason, not as a success', async () => {
    spies.changeUserPassword.mockResolvedValue(false);

    const status = await useChangePassword().changePassword(PAYLOAD);

    expect(status).toEqual({ message: 'common.change_not_applied', success: false });
    expect(spies.colibriLogin).not.toHaveBeenCalled();
  });

  it('should hand a change that threw back with the backend message', async () => {
    spies.changeUserPassword.mockRejectedValue(new Error('wrong password'));

    const status = await useChangePassword().changePassword(PAYLOAD);

    expect(status).toEqual({ message: 'wrong password', success: false });
  });
});
