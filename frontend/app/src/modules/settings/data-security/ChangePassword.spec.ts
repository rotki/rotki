import { type DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import ChangePassword from '@/modules/settings/data-security/ChangePassword.vue';

const { changePassword } = vi.hoisted(() => ({
  changePassword: vi.fn(),
}));

vi.mock('@/modules/auth/use-change-password', () => ({
  useChangePassword: (): { changePassword: typeof changePassword } => ({ changePassword }),
}));

type ChangePasswordInstance = InstanceType<typeof ChangePassword>;

describe('settings/data-security/ChangePassword.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<ChangePasswordInstance>;

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    changePassword.mockReset();
    changePassword.mockResolvedValue({ success: true });
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(): VueWrapper<ChangePasswordInstance> {
    return mount(ChangePassword, {
      global: {
        plugins: [pinia],
      },
    });
  }

  function field(name: 'current-password' | 'new-password' | 'confirm-password'): DOMWrapper<HTMLInputElement> {
    return wrapper.find<HTMLInputElement>(`[data-testid=${name}] input`);
  }

  function submitButton(): DOMWrapper<HTMLButtonElement> {
    return wrapper.find<HTMLButtonElement>('[data-testid=change-password-button]');
  }

  async function fill(current: string, next: string, confirm: string): Promise<void> {
    await field('current-password').setValue(current);
    await field('new-password').setValue(next);
    await field('confirm-password').setValue(confirm);
  }

  it('should disable the submit button until every field is filled', async () => {
    wrapper = createWrapper();

    expect(submitButton().attributes('disabled')).toBeDefined();

    await fill('old', 'new', 'new');

    expect(submitButton().attributes('disabled')).toBeUndefined();
  });

  it('should reject a confirmation that does not match the new password', async () => {
    wrapper = createWrapper();

    await fill('old', 'new', 'different');

    expect(wrapper.find('[data-testid=confirm-password] .details .text-rui-error').text())
      .toBe('change_password.validation.password_mismatch');
    expect(submitButton().attributes('disabled')).toBeDefined();
  });

  it('should submit the current and the new password', async () => {
    wrapper = createWrapper();

    await fill('old', 'new', 'new');
    await wrapper.find('form').trigger('submit');

    expect(changePassword).toHaveBeenCalledWith({ currentPassword: 'old', newPassword: 'new' });
  });

  it('should clear the form once the password was changed', async () => {
    wrapper = createWrapper();

    await fill('old', 'new', 'new');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(field('current-password').element.value).toBe('');
    expect(field('new-password').element.value).toBe('');
    expect(field('confirm-password').element.value).toBe('');
  });

  it('should keep what was typed when the change failed', async () => {
    changePassword.mockResolvedValue({ message: 'wrong password', success: false });
    wrapper = createWrapper();

    await fill('old', 'new', 'new');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(field('current-password').element.value).toBe('old');
    expect(field('new-password').element.value).toBe('new');
  });
});
