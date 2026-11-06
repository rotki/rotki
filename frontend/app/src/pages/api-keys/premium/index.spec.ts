import { externalLinks } from '@shared/external-links';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { type DOMWrapper, mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises/index';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremium } from '@/modules/premium/use-premium';
import { usePremiumCredentialsApi } from '@/modules/premium/use-premium-credentials-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import PremiumSettings from '@/pages/api-keys/premium/index.vue';

vi.mock('@/modules/shell/app/use-electron-interop', (): Record<string, unknown> => ({
  useInterop: vi.fn().mockReturnValue(createMock<ReturnType<typeof useInterop>>({
    openUrl: vi.fn(async () => {}),
    premiumUserLoggedIn: vi.fn(),
  })),
}));

vi.mock('@/modules/premium/use-premium-credentials-api', (): Record<string, unknown> => ({
  usePremiumCredentialsApi: vi.fn().mockReturnValue({
    deletePremiumCredentials: vi.fn(),
    getPremiumCapabilities: vi.fn().mockResolvedValue({}),
    setPremiumCredentials: vi.fn(),
  }),
}));

describe('premium-settings', () => {
  let wrapper: VueWrapper<InstanceType<typeof PremiumSettings>>;
  let api: ReturnType<typeof usePremiumCredentialsApi>;

  function createWrapper(): VueWrapper<InstanceType<typeof PremiumSettings>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(PremiumSettings, {
      global: {
        plugins: [pinia],
        stubs: ['i18n-t', 'card-title'],
        provide: libraryDefaults,
      },
    });
  }

  beforeEach((): void => {
    document.body.dataset.app = 'true';
    wrapper = createWrapper();
    api = usePremiumCredentialsApi();
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  it('should update premium status upon setting keys', async () => {
    api.setPremiumCredentials = vi.fn().mockResolvedValue({ result: true });
    const apiKey = wrapper.find('[data-testid=premium-api-key] input');
    const apiSecret = wrapper.find('[data-testid=premium-api-secret] input');

    await apiKey.setValue('1234');
    await apiSecret.setValue('1234');

    await nextTick();
    await wrapper.find('[data-testid=premium-setup]').trigger('click');
    await nextTick();
    await flushPromises();

    const { premiumUserLoggedIn } = useInterop();
    expect(premiumUserLoggedIn).toHaveBeenCalledWith(true);
  });

  function field(name: 'api-key' | 'api-secret'): DOMWrapper<HTMLInputElement> {
    return wrapper.find<HTMLInputElement>(`[data-testid=premium-${name}] input`);
  }

  function fieldError(name: 'api-key' | 'api-secret'): string {
    return wrapper.find(`[data-testid=premium-${name}] .details .text-rui-error`).text();
  }

  async function submit(): Promise<void> {
    await wrapper.find('[data-testid=premium-setup]').trigger('click');
    await nextTick();
    await flushPromises();
  }

  it('should not submit without an api key and secret', async () => {
    api.setPremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await submit();

    expect(api.setPremiumCredentials).not.toHaveBeenCalled();
  });

  it('should not submit with only the api key filled', async () => {
    api.setPremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await field('api-key').setValue('1234');
    await submit();

    expect(api.setPremiumCredentials).not.toHaveBeenCalled();
  });

  it('should report both missing fields once submitted', async () => {
    await submit();

    expect(fieldError('api-key')).not.toBe('');
    expect(fieldError('api-secret')).not.toBe('');
  });

  it('should reject a whitespace only api key', async () => {
    api.setPremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await field('api-key').setValue('   ');
    await field('api-secret').setValue('1234');
    await submit();

    expect(api.setPremiumCredentials).not.toHaveBeenCalled();
  });

  it('should clear the fields once the credentials were accepted', async () => {
    api.setPremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await field('api-key').setValue('1234');
    await field('api-secret').setValue('5678');
    await submit();

    expect(field('api-key').element.value).toBe('');
    expect(field('api-secret').element.value).toBe('');
  });

  it('should name a refused save above the cards, keeping what was typed', async () => {
    api.setPremiumCredentials = vi.fn().mockRejectedValue(new Error('invalid api key'));

    await field('api-key').setValue('1234');
    await field('api-secret').setValue('5678');
    await submit();

    const strip = wrapper.find('[data-testid=premium-settings-failure]');
    expect(strip.text()).toContain('invalid api key');
    expect(field('api-key').element.value).toBe('1234');
  });

  it('should drop the named failure when the next save starts', async () => {
    api.setPremiumCredentials = vi.fn().mockRejectedValueOnce(new Error('invalid api key')).mockResolvedValue(true);

    await field('api-key').setValue('1234');
    await field('api-secret').setValue('5678');
    await submit();
    await submit();

    expect(wrapper.find('[data-testid=premium-settings-failure]').exists()).toBe(false);
  });

  async function refuseForDeviceLimit(): Promise<void> {
    api.setPremiumCredentials = vi.fn().mockRejectedValue(new Error('too many devices _DEVICE_LIMIT_LINK_'));

    await field('api-key').setValue('1234');
    await field('api-secret').setValue('5678');
    await submit();
  }

  it('should name a device limit refusal in the strip, without the link marker', async () => {
    await refuseForDeviceLimit();

    const strip = wrapper.find('[data-testid=premium-settings-failure]');
    expect(strip.text()).toContain('too many devices');
    expect(strip.text()).not.toContain('_DEVICE_LIMIT_LINK_');
    expect(document.body.querySelector('[data-testid=inline-confirm]')).toBeNull();
  });

  it('should open the devices page from the device limit strip', async () => {
    await refuseForDeviceLimit();

    await wrapper.find('[data-testid=premium-settings-device-limit-learn-more]').trigger('click');

    const { openUrl } = useInterop();
    expect(openUrl).toHaveBeenCalledWith(externalLinks.premiumDevices);
  });

  it('should offer the devices link only for a device limit refusal', async () => {
    api.setPremiumCredentials = vi.fn().mockRejectedValue(new Error('invalid api key'));

    await field('api-key').setValue('1234');
    await field('api-secret').setValue('5678');
    await submit();

    expect(wrapper.find('[data-testid=premium-settings-failure]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=premium-settings-device-limit-learn-more]').exists()).toBe(false);
  });

  async function askToRemove(): Promise<void> {
    set(usePremium(), true);
    await nextTick();
    api.deletePremiumCredentials = vi.fn().mockResolvedValue({ result: true });

    await wrapper.find('[data-testid=premium-delete]').trigger('click');
    await nextTick();
    await flushPromises();
  }

  function questionButton(testId: 'inline-confirm-accept' | 'inline-confirm-cancel'): HTMLElement {
    const button = document.body.querySelector<HTMLElement>(`[data-testid=${testId}]`);
    assert(button);
    return button;
  }

  it('should ask beside the remove button and keep the keys until accepted', async () => {
    await askToRemove();

    expect(document.body.querySelector('[data-testid=inline-confirm]')?.textContent).toContain('premium_settings.delete_confirmation.message');
    expect(api.deletePremiumCredentials).not.toHaveBeenCalled();
  });

  it('should update premium status upon removing keys', async () => {
    await askToRemove();

    questionButton('inline-confirm-accept').click();
    await flushPromises();

    const { premiumUserLoggedIn } = useInterop();
    expect(premiumUserLoggedIn).toHaveBeenCalledWith(false);
  });

  it('should keep the keys when the question is cancelled', async () => {
    await askToRemove();

    questionButton('inline-confirm-cancel').click();
    await flushPromises();

    expect(api.deletePremiumCredentials).not.toHaveBeenCalled();
  });
});
