import { DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import PasswordConfirmationSetting from '@/modules/settings/data-security/PasswordConfirmationSetting.vue';

const { updateFrontendSetting } = vi.hoisted(() => ({
  updateFrontendSetting: vi.fn(),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): { updateFrontendSetting: typeof updateFrontendSetting } => ({ updateFrontendSetting }),
}));

type SettingInstance = InstanceType<typeof PasswordConfirmationSetting>;

const SECONDS_PER_DAY = 86400;

describe('settings/data-security/PasswordConfirmationSetting.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<SettingInstance>;

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    updateFrontendSetting.mockReset();
    updateFrontendSetting.mockResolvedValue(undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
    // The confirm dialog is teleported into the body; a leftover one would let the next test click a
    // stale button and pass without rendering its own.
    document.body.innerHTML = '';
  });

  function createWrapper(): VueWrapper<SettingInstance> {
    return mount(PasswordConfirmationSetting, {
      global: {
        plugins: [pinia],
      },
    });
  }

  function intervalInput(): DOMWrapper<HTMLInputElement> {
    return wrapper.find<HTMLInputElement>('[data-testid=password-confirmation-interval-input] input');
  }

  function saveButton(): DOMWrapper<HTMLButtonElement> {
    return wrapper.find<HTMLButtonElement>('[data-testid=save-password-confirmation-settings]');
  }

  function errorMessage(): string {
    return wrapper.find('[data-testid=password-confirmation-interval-input] .details .text-rui-error').text();
  }

  function toggle(): DOMWrapper<HTMLInputElement> {
    return wrapper.find<HTMLInputElement>('[data-testid=enable-password-confirmation-toggle] input');
  }

  /** The confirm dialog is teleported to the body, so it is reached through the document. */
  async function confirmDisable(): Promise<void> {
    const confirm = document.body.querySelector<HTMLButtonElement>('[data-testid=button-confirm]');
    assert(confirm, 'the disable warning is not showing');
    await new DOMWrapper(confirm).trigger('click');
    await flushPromises();
  }

  it('should not offer to save while nothing has changed', () => {
    wrapper = createWrapper();

    expect(saveButton().attributes('disabled')).toBeDefined();
  });

  it('should persist a changed interval in seconds', async () => {
    wrapper = createWrapper();

    await intervalInput().setValue('14');
    expect(saveButton().attributes('disabled')).toBeUndefined();

    await saveButton().trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith({
      enablePasswordConfirmation: true,
      passwordConfirmationInterval: 14 * SECONDS_PER_DAY,
    });
  });

  it('should reject an interval outside the allowed range', async () => {
    wrapper = createWrapper();

    await intervalInput().setValue('9999');

    expect(errorMessage()).toBe('password_confirmation_setting.validation.range');
    expect(saveButton().attributes('disabled')).toBeDefined();
  });

  it('should reject an empty interval', async () => {
    wrapper = createWrapper();

    await intervalInput().setValue('');

    expect(errorMessage()).toBe('password_confirmation_setting.validation.range');
    expect(saveButton().attributes('disabled')).toBeDefined();
  });

  // Turning the confirmation off weakens the account, so it goes through a ConfirmDialog rather than
  // applying straight away.
  it('should not disable the confirmation until the warning is accepted', async () => {
    wrapper = createWrapper();

    await toggle().setValue(false);

    // The interval field follows the setting, so it staying editable is what proves nothing changed.
    expect(intervalInput().attributes('disabled')).toBeUndefined();
    expect(saveButton().attributes('disabled')).toBeDefined();
  });

  it('should disable the confirmation once the warning is accepted', async () => {
    wrapper = createWrapper();

    await toggle().setValue(false);
    await confirmDisable();

    expect(intervalInput().attributes('disabled')).toBeDefined();

    await saveButton().trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith(expect.objectContaining({
      enablePasswordConfirmation: false,
    }));
  });

  it('should not save an invalid interval even if the button is reached', async () => {
    wrapper = createWrapper();

    await intervalInput().setValue('9999');
    await saveButton().trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });
});
