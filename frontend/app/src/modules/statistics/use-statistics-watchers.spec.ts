import { type ComponentMountingOptions, mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { useStatisticsWatchers } from './use-statistics-watchers';
import '@test/i18n';

const mockFetchNetValue = vi.fn();
const mockPremium = ref<boolean>(false);
const mockLogged = ref<boolean>(true);

vi.mock('@/composables/premium', () => ({
  usePremium: vi.fn(() => mockPremium),
}));

vi.mock('@/modules/session/use-session-auth-store', () => ({
  useSessionAuthStore: vi.fn(() => ({
    logged: mockLogged,
  })),
}));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: vi.fn(() => ({
    fetchNetValue: mockFetchNetValue,
  })),
}));

function mountWithWatcher(options?: ComponentMountingOptions<object>): ReturnType<typeof mount> {
  return mount(defineComponent({
    setup() {
      useStatisticsWatchers();
      return {};
    },
    render: () => null,
  }), options);
}

describe('useStatisticsWatchers', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockFetchNetValue.mockResolvedValue(undefined);
    set(mockPremium, false);
    set(mockLogged, true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch net value when premium changes and user is logged in', async () => {
    const wrapper = mountWithWatcher();

    set(mockPremium, true);
    await flushPromises();

    expect(mockFetchNetValue).toHaveBeenCalledOnce();
    wrapper.unmount();
  });

  it('should not fetch net value when premium changes but user is not logged in', async () => {
    set(mockLogged, false);
    const wrapper = mountWithWatcher();

    set(mockPremium, true);
    await flushPromises();

    expect(mockFetchNetValue).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it('should not fetch net value on initial setup (only on change)', async () => {
    const wrapper = mountWithWatcher();
    await flushPromises();

    expect(mockFetchNetValue).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
