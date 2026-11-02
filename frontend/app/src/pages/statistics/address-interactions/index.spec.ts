import type { useAddressInteractions } from '@/modules/statistics/address-interactions/use-address-interactions';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import AddressInteractionsPage from '@/pages/statistics/address-interactions/index.vue';
import '@test/i18n';

const { allowed, refresh } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { allowed: ref<boolean>(false), refresh: vi.fn<() => Promise<void>>() };
});

vi.mock('@/modules/premium/use-feature-access', async () => {
  const { computed } = await import('vue');
  return {
    PremiumFeature: { GRAPHS_VIEW: 'graphsView' },
    useFeatureAccess: (): Record<string, unknown> => ({
      allowed: computed<boolean>(() => get(allowed)),
      minimumTier: computed<string | null>(() => null),
    }),
  };
});

vi.mock('@/modules/statistics/address-interactions/use-address-interactions', async () => {
  const { shallowRef } = await import('vue');
  return {
    useAddressInteractions: (): ReturnType<typeof useAddressInteractions> => ({
      error: shallowRef<string>(),
      interactions: shallowRef([]),
      loading: shallowRef<boolean>(false),
      refresh,
    }),
  };
});

function createWrapper(): VueWrapper {
  return mount(AddressInteractionsPage, {
    global: {
      stubs: {
        AddressInteractionGraph: true,
        AddressInteractionsPlaceholder: { template: '<div data-testid="address-interactions-placeholder" />' },
        RouterLink: true,
        TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
      },
    },
  });
}

describe('pages/statistics/address-interactions', () => {
  beforeEach(() => {
    set(allowed, false);
    refresh.mockReset().mockResolvedValue();
  });

  it('should show the premium placeholder and request nothing without the graphs capability', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=address-interactions-placeholder]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=address-interactions-refresh]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=address-interactions-empty]').exists()).toBe(false);
    expect(refresh).not.toHaveBeenCalled();
  });

  it('should load the interactions with the graphs capability', () => {
    set(allowed, true);
    const wrapper = createWrapper();

    expect(refresh).toHaveBeenCalledOnce();
    expect(wrapper.find('[data-testid=address-interactions-placeholder]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=address-interactions-refresh]').exists()).toBe(true);
  });

  it('should load the interactions when the capability arrives after the page mounted', async () => {
    const wrapper = createWrapper();
    set(allowed, true);
    await nextTick();

    expect(refresh).toHaveBeenCalledOnce();
    expect(wrapper.find('[data-testid=address-interactions-placeholder]').exists()).toBe(false);
  });
});
