import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BalanceViewPicker from '@/modules/balances/components/BalanceViewPicker.vue';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';

const h = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    attention: ref<number>(0),
    available: ref<boolean>(true),
    ensureSummary: vi.fn<() => Promise<void>>(),
    isHistory: ref<boolean>(false),
  };
});

vi.mock('@/modules/core/common/feature-flags', () => ({ isAccountingUpdateEnabled: (): boolean => true }));
vi.mock('@/modules/balances/view/use-balance-view', () => ({
  useBalanceView: (): object => ({ available: h.available, isHistory: h.isHistory }),
}));
vi.mock('@/modules/history/reconciliation/use-bucket-reconciliation', () => ({
  useBucketReconciliation: (): object => ({ attention: h.attention, ensureSummary: h.ensureSummary }),
}));

const RuiMenuStub = {
  template: '<div data-testid="balance-view-picker"><slot name="activator" :attrs="{}" /><slot /></div>',
};

function mountPicker(): VueWrapper {
  return mount(BalanceViewPicker, { global: { stubs: { BalanceViewPanel: true, RuiMenu: RuiMenuStub } } });
}

function dotIsShown(wrapper: VueWrapper): boolean {
  return !wrapper.get('[data-testid="balance-view-attention"]').classes().includes('invisible');
}

describe('balanceViewPicker', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    h.available.value = true;
    h.attention.value = 0;
    h.isHistory.value = false;
    h.ensureSummary.mockReset().mockResolvedValue(undefined);
  });

  it('should render nothing and load no summary when the history view is not available', async () => {
    h.available.value = false;
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="balance-view-picker-trigger"]').exists()).toBe(false);
    expect(h.ensureSummary).not.toHaveBeenCalled();
  });

  it('should load the reconciliation summary once the picker is offered', async () => {
    mountPicker();
    await flushPromises();

    expect(h.ensureSummary).toHaveBeenCalledOnce();
  });

  it('should keep both view labels in the trigger, so switching views keeps its width', () => {
    const labels = mountPicker().get('[data-testid="balance-view-picker-trigger"]').text();

    expect(labels).toContain('balance_view.live');
    expect(labels).toContain('balance_view.history');
  });

  it('should show the dot when reconciliation has items needing attention', async () => {
    h.attention.value = 2;
    const wrapper = mountPicker();
    await flushPromises();

    expect(dotIsShown(wrapper)).toBe(true);
  });

  it('should show the dot when the snapshot is behind recent event edits', async () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: [], processingRequired: false, stale: true });
    const wrapper = mountPicker();
    await flushPromises();

    expect(dotIsShown(wrapper)).toBe(true);
  });

  it('should show the dot in the error colour when the snapshot failed to load', async () => {
    useHistoricalSnapshotStore().setError('backend down');
    const wrapper = mountPicker();
    await flushPromises();

    expect(dotIsShown(wrapper)).toBe(true);
    expect(wrapper.get('[data-testid="balance-view-attention"]').classes()).toContain('bg-rui-error');
  });

  it('should keep the dot hidden, but in place, when history agrees and is current', async () => {
    useHistoricalSnapshotStore().setSnapshot({ entries: [], processingRequired: false, stale: false });
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="balance-view-attention"]').exists()).toBe(true);
    expect(dotIsShown(wrapper)).toBe(false);
  });
});
