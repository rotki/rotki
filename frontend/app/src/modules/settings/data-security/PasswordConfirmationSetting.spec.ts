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
    vi.useFakeTimers();
    updateFrontendSetting.mockReset();
    updateFrontendSetting.mockResolvedValue(undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
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

  function errorMessage(): string {
    return wrapper.find('[data-testid=password-confirmation-interval-input] .details .text-rui-error').text();
  }

  function toggle(): DOMWrapper<HTMLInputElement> {
    return wrapper.find<HTMLInputElement>('[data-testid=enable-password-confirmation-toggle] input');
  }

  /** Lets the debounced interval write run. */
  async function settle(): Promise<void> {
    await vi.runAllTimersAsync();
    await flushPromises();
  }

  /** The confirm dialog is teleported to the body, so it is reached through the document. */
  async function confirmDisable(): Promise<void> {
    const confirm = document.body.querySelector<HTMLButtonElement>('[data-testid=button-confirm]');
    assert(confirm, 'the disable warning is not showing');
    await new DOMWrapper(confirm).trigger('click');
    await flushPromises();
  }

  it('should persist a changed interval in seconds without a save step', async () => {
    wrapper = createWrapper();

    await intervalInput().setValue('14');
    await settle();

    expect(updateFrontendSetting).toHaveBeenCalledWith({
      enablePasswordConfirmation: true,
      passwordConfirmationInterval: 14 * SECONDS_PER_DAY,
    });
  });

  it('should write once for a burst of typing', async () => {
    wrapper = createWrapper();

    await intervalInput().setValue('1');
    await intervalInput().setValue('12');
    await settle();

    expect(updateFrontendSetting).toHaveBeenCalledTimes(1);
    expect(updateFrontendSetting).toHaveBeenCalledWith(expect.objectContaining({
      passwordConfirmationInterval: 12 * SECONDS_PER_DAY,
    }));
  });

  it('should reject and not save an interval outside the allowed range', async () => {
    wrapper = createWrapper();

    await intervalInput().setValue('9999');
    await settle();

    expect(errorMessage()).toBe('password_confirmation_setting.validation.range');
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should reject and not save an empty interval', async () => {
    wrapper = createWrapper();

    await intervalInput().setValue('');
    await settle();

    expect(errorMessage()).toBe('password_confirmation_setting.validation.range');
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should not disable the confirmation until the warning is accepted', async () => {
    wrapper = createWrapper();

    await toggle().setValue(false);
    await settle();

    // The interval field follows the setting, so it staying editable is what proves nothing changed.
    expect(intervalInput().attributes('disabled')).toBeUndefined();
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should save the disabled confirmation once the warning is accepted', async () => {
    wrapper = createWrapper();

    await toggle().setValue(false);
    await confirmDisable();
    await settle();

    expect(intervalInput().attributes('disabled')).toBeDefined();
    expect(updateFrontendSetting).toHaveBeenCalledWith(expect.objectContaining({
      enablePasswordConfirmation: false,
    }));
  });
});
