import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EventAssetPriceUpdateDialog from '@/modules/history/events/prices/EventAssetPriceUpdateDialog.vue';
import '@test/i18n';

const { loadError, retryLoad, saveError } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return {
    loadError: shallowRef<unknown>(),
    retryLoad: vi.fn<() => Promise<void>>(),
    saveError: shallowRef<unknown>(),
  };
});

vi.mock('@/modules/history/events/prices/use-event-price-update-dialog', async () => {
  const { computed, ref, shallowRef } = await import('vue');
  return {
    useEventPriceUpdateDialog: (): Record<string, unknown> => ({
      close: vi.fn(),
      existingEntry: shallowRef(),
      loadError,
      loading: shallowRef<boolean>(false),
      modelMode: ref('manual'),
      modelPrice: ref('1600'),
      open: computed<boolean>(() => true),
      priceErrors: computed<string[]>(() => []),
      priceValid: computed<boolean>(() => true),
      retryLoad,
      save: vi.fn(),
      saveError,
      saving: shallowRef<boolean>(false),
      showModeChoice: computed<boolean>(() => false),
    }),
  };
});

const payload: EventPriceUpdatePayload = { asset: 'ETH', timestamp: 1_700_000_000_000 };

function mountDialog(): VueWrapper {
  const pinia = createCustomPinia();
  setActivePinia(pinia);
  return mount(EventAssetPriceUpdateDialog, {
    global: {
      plugins: [pinia],
      provide: libraryDefaults,
      stubs: {
        AmountInput: true,
        AssetDetails: true,
        DateDisplay: true,
        RuiDialog: { template: '<div><slot /></div>' },
      },
    },
    props: { modelValue: payload },
  });
}

function saveButton(wrapper: VueWrapper): ReturnType<VueWrapper['find']> {
  const button = wrapper.findAll('button').find(candidate => candidate.text() === 'common.actions.save');
  if (!button)
    throw new Error('no save button');
  return button;
}

describe('eventAssetPriceUpdateDialog', () => {
  beforeEach(() => {
    set(loadError, undefined);
    set(saveError, undefined);
    retryLoad.mockClear();
  });

  it('should name a failed read, read again from there, and block saving', async () => {
    set(loadError, new Error('offline'));
    const wrapper = mountDialog();

    const strip = wrapper.find('[data-testid=event-price-load-error]');
    expect(strip.text()).toContain('offline');
    expect(saveButton(wrapper).attributes('disabled')).toBeDefined();
    await strip.find('[data-testid=table-failure-strip-retry]').trigger('click');

    expect(retryLoad).toHaveBeenCalledOnce();
  });

  it('should name a failed save without a retry of its own, leaving save usable', () => {
    set(saveError, new Error('rejected'));
    const wrapper = mountDialog();

    const strip = wrapper.find('[data-testid=event-price-save-error]');
    expect(strip.text()).toContain('rejected');
    expect(strip.find('[data-testid=table-failure-strip-retry]').exists()).toBe(false);
    expect(saveButton(wrapper).attributes('disabled')).toBeUndefined();
  });

  it('should show no failure while nothing failed', () => {
    const wrapper = mountDialog();

    expect(wrapper.find('[data-testid=table-failure-strip]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=event-price-load-error]').exists()).toBe(false);
  });
});
