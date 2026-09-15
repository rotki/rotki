import type { ExternalServiceName } from '@/modules/integrations/types';
import type { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { externalLinks } from '@shared/external-links';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useRouter } from 'vue-router';
import { EXTERNAL_API_KEY_SERVICES, type ExternalApiKeyService } from '@/modules/settings/api-keys/external/external-api-key-services';

type ExternalApiKeysMock = Pick<ReturnType<typeof useExternalApiKeys>, 'actionStatus' | 'confirmDelete' | 'loading' | 'save' | 'useApiKey'>;

const savedKeys = ref<Partial<Record<ExternalServiceName, string>>>({});
const confirmDelete = vi.fn<ExternalApiKeysMock['confirmDelete']>();
const save = vi.fn<ExternalApiKeysMock['save']>();

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: (): ExternalApiKeysMock => ({
    actionStatus: () => computed(() => undefined),
    confirmDelete,
    loading: readonly(ref<boolean>(false)),
    save,
    useApiKey: name => computed<string>(() => get(savedKeys)[toValue(name)] ?? ''),
  }),
}));

const ExternalApiKeyCard = (await import('@/modules/settings/api-keys/external/ExternalApiKeyCard.vue')).default;

type Wrapper = VueWrapper<InstanceType<typeof ExternalApiKeyCard>>;

function createWrapper(service: ExternalApiKeyService): Wrapper {
  return mount(ExternalApiKeyCard, {
    global: {
      plugins: [createCustomPinia()],
      stubs: {
        I18nT: { props: ['keypath'], template: '<div>{{ keypath }}<slot name="link" /></div>' },
        Teleport: { template: '<span><slot /></span>' },
        Transition: { template: '<span><slot /></span>' },
      },
    },
    props: { service },
  });
}

async function openDialog(wrapper: Wrapper): Promise<void> {
  const trigger = wrapper
    .findAll('button')
    .find(button => /external_services\.actions\.(enter_api_key|replace_key)/.test(button.text()));
  await trigger?.trigger('click');
  await vi.advanceTimersToNextTimerAsync();
}

async function typeAndConfirm(wrapper: Wrapper, apiKey: string): Promise<void> {
  await wrapper.find('[data-testid=bottom-dialog] [data-testid=service-key-api-key] input').setValue(apiKey);
  await nextTick();
  await wrapper.find('form').trigger('submit');
  await flushPromises();
}

describe('externalApiKeyCard', () => {
  beforeEach(async () => {
    document.body.dataset.app = 'true';
    setActivePinia(createCustomPinia());
    vi.useFakeTimers();
    await useRouter().replace({ query: {} });
    set(savedKeys, {});
    confirmDelete.mockReset();
    save.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should present the title, description and key hint of the service it is given', async () => {
    const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.alchemy);

    expect(wrapper.text()).toContain('external_services.alchemy.title');
    expect(wrapper.text()).toContain('external_services.alchemy.description');

    await openDialog(wrapper);

    expect(wrapper.find('[data-testid=bottom-dialog]').text()).toContain('external_services.alchemy.hint');
  });

  it('should link to the page where the key is obtained', async () => {
    const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.alchemy);
    await openDialog(wrapper);

    expect(wrapper.find('[data-testid=bottom-dialog] a').attributes('href')).toBe(externalLinks.alchemyApiKey);
  });

  it('should not offer where to get a key for a service that has no link', async () => {
    const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.cryptocompare);
    await openDialog(wrapper);

    expect(wrapper.find('[data-testid=bottom-dialog]').text()).not.toContain('external_services.get_api_key');
  });

  it('should keep delete disabled while no key is saved', async () => {
    const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.alchemy);
    await openDialog(wrapper);

    expect(wrapper.find('[data-testid=bottom-dialog] [data-testid=delete-button]').attributes()).toHaveProperty('disabled');
  });

  it('should ask to confirm deleting the saved key of its own service', async () => {
    set(savedKeys, { alchemy: 'saved-key' });
    const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.alchemy);
    await openDialog(wrapper);

    await wrapper.find('[data-testid=bottom-dialog] [data-testid=delete-button]').trigger('click');

    expect(confirmDelete).toHaveBeenCalledWith('alchemy');
  });

  it('should keep save disabled until a key is typed', async () => {
    const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.birdeye);
    await openDialog(wrapper);

    expect(wrapper.find('[data-testid=bottom-dialog] [data-testid=confirm]').attributes()).toHaveProperty('disabled');

    await wrapper.find('[data-testid=bottom-dialog] [data-testid=service-key-api-key] input').setValue('typed-key');
    await nextTick();

    expect(wrapper.find('[data-testid=bottom-dialog] [data-testid=confirm]').attributes()).not.toHaveProperty('disabled');
  });

  it('should save the typed key under the service name, with no follow-up action', async () => {
    const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.etherscan);
    await openDialog(wrapper);

    await typeAndConfirm(wrapper, 'typed-key');

    expect(save).toHaveBeenCalledExactlyOnceWith({ apiKey: 'typed-key', name: 'etherscan' });
  });

  describe('a link to the page naming a service', () => {
    it('should open the card of that service', async () => {
      await useRouter().push({ query: { service: 'alchemy' } });
      const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.alchemy);
      await vi.advanceTimersToNextTimerAsync();

      expect(wrapper.find('[data-testid=bottom-dialog]').exists()).toBe(true);
    });

    it('should leave the card of another service closed', async () => {
      await useRouter().push({ query: { service: 'etherscan' } });
      const wrapper = createWrapper(EXTERNAL_API_KEY_SERVICES.alchemy);
      await vi.advanceTimersToNextTimerAsync();

      expect(wrapper.find('[data-testid=bottom-dialog]').exists()).toBe(false);
    });
  });
});
