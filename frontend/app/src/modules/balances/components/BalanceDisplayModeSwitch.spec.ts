import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import BalanceDisplayModeSwitch from '@/modules/balances/components/BalanceDisplayModeSwitch.vue';
import { useBalanceDisplayModeStore } from '@/modules/balances/use-balance-display-mode-store';

const h = vi.hoisted(() => ({
  attention: { value: 0 },
  ensureSummary: vi.fn<() => Promise<void>>(),
  triggerProcessing: vi.fn<() => Promise<void>>(),
}));

vi.mock('@/modules/balances/use-current-historical-balances', () => ({
  useCurrentHistoricalBalances: (): Record<string, unknown> => ({
    ensureLoaded: vi.fn(),
    loading: ref(false),
    refresh: vi.fn(),
    triggerProcessing: h.triggerProcessing,
  }),
}));
vi.mock('@/modules/history/reconciliation/use-bucket-reconciliation', () => ({
  useBucketReconciliation: (): Record<string, unknown> => ({
    attention: ref(h.attention.value),
    ensureSummary: h.ensureSummary,
  }),
}));

const RouterLinkStub = { props: ['to'], template: '<a><slot /></a>' };

function mountSwitch(): ReturnType<typeof mount> {
  return mount(BalanceDisplayModeSwitch, { global: { stubs: { RouterLink: RouterLinkStub } } });
}

describe('balanceDisplayModeSwitch', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    h.attention.value = 0;
    h.ensureSummary.mockResolvedValue(undefined);
    h.triggerProcessing.mockResolvedValue(undefined);
  });

  it('should render nothing and fetch nothing when the accounting update is off', async () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', '');
    const wrapper = mountSwitch();
    await flushPromises();

    expect(wrapper.find('[data-testid="balance-display-mode-switch"]').exists()).toBe(false);
    expect(h.ensureSummary).not.toHaveBeenCalled();
  });

  it('should render and load the reconciliation summary when enabled', async () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', 'true');
    const wrapper = mountSwitch();
    await flushPromises();

    expect(wrapper.find('[data-testid="balance-display-mode-switch"]').exists()).toBe(true);
    expect(h.ensureSummary).toHaveBeenCalledOnce();
  });

  it('should offer processing and the reconciliation link only in history mode when stale', async () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', 'true');
    const store = useBalanceDisplayModeStore();
    store.setSnapshot({ entries: [], processingRequired: false, stale: true });
    const wrapper = mountSwitch();
    expect(wrapper.find('[data-testid="balance-display-mode-notice"]').exists()).toBe(false);

    store.setMode('history');
    await flushPromises();
    expect(wrapper.find('[data-testid="balance-display-mode-reconciliation-link"]').exists()).toBe(true);

    await wrapper.get('[data-testid="balance-display-mode-process"]').trigger('click');
    expect(h.triggerProcessing).toHaveBeenCalledOnce();
  });
});
