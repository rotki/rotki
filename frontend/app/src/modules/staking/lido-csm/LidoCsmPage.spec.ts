import type { LidoCsmNodeOperator } from '@/modules/staking/staking-types';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import LidoCsmPage from '@/modules/staking/lido-csm/LidoCsmPage.vue';

interface ApiResult {
  entries: LidoCsmNodeOperator[];
  message: string;
}

const { fetchPrices, listNodeOperators, refreshMetrics } = vi.hoisted(() => ({
  fetchPrices: vi.fn<() => Promise<void>>(async () => undefined),
  listNodeOperators: vi.fn<() => Promise<ApiResult>>(),
  refreshMetrics: vi.fn<() => Promise<ApiResult>>(),
}));

vi.mock('@/modules/staking/api/use-lido-csm-api', () => ({
  useLidoCsmApi: (): Record<string, unknown> => ({ listNodeOperators, refreshMetrics }),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): Record<string, unknown> => ({ fetchPrices }),
}));

const AddDialogStub = {
  emits: ['added', 'update:modelValue'],
  name: 'LidoCsmAddDialog',
  props: ['modelValue'],
  template: '<div />',
};

function createWrapper(): VueWrapper {
  return mount(LidoCsmPage, {
    global: {
      stubs: {
        LidoCsmAddDialog: AddDialogStub,
        LidoCsmTable: { emits: ['add', 'refresh'], name: 'LidoCsmTable', props: ['rows', 'loading'], template: '<div />' },
        LidoCsmTotals: true,
        RuiTooltip: { template: '<div><slot name="activator" /></div>' },
        StakingLocationTitle: true,
        TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
      },
    },
  });
}

function strip(wrapper: VueWrapper): VueWrapper<any> {
  return wrapper.findComponent(FailureStrip);
}

describe('modules/staking/lido-csm/LidoCsmPage.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listNodeOperators.mockResolvedValue({ entries: [], message: '' });
    refreshMetrics.mockResolvedValue({ entries: [], message: '' });
  });

  it('should show no failure once the operators load', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(strip(wrapper).exists()).toBe(false);
  });

  it('should name a failed load above the table', async () => {
    const error = new Error('backend down');
    listNodeOperators.mockRejectedValue(error);

    const wrapper = createWrapper();
    await flushPromises();

    expect(strip(wrapper).props('failure')).toBe(error);
    expect(strip(wrapper).props('title')).toBe('staking_page.lido_csm.messages.fetch_failed');
  });

  it('should name the metrics the backend could not fetch while still listing the operators', async () => {
    listNodeOperators.mockResolvedValue({ entries: [], message: 'Failed to fetch metrics for node operator 5' });

    const wrapper = createWrapper();
    await flushPromises();

    expect(strip(wrapper).props('failure')).toBe('Failed to fetch metrics for node operator 5');
  });

  it('should retry by refreshing the metrics, and drop the failure once that succeeds', async () => {
    listNodeOperators.mockRejectedValue(new Error('backend down'));
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid=failure-strip-retry]').trigger('click');
    await flushPromises();

    expect(refreshMetrics).toHaveBeenCalledOnce();
    expect(strip(wrapper).exists()).toBe(false);
  });

  describe('after an operator is added', () => {
    async function addWith(warning: string | undefined): Promise<VueWrapper> {
      const wrapper = createWrapper();
      await flushPromises();
      await wrapper.findComponent({ name: 'LidoCsmTable' }).vm.$emit('add');
      await nextTick();
      wrapper.findComponent(AddDialogStub).vm.$emit('added', warning);
      await flushPromises();
      return wrapper;
    }

    it('should reload the operators', async () => {
      await addWith(undefined);

      expect(listNodeOperators).toHaveBeenCalledTimes(2);
    });

    it('should keep what the add could not fetch in view as a retryable failure', async () => {
      const wrapper = await addWith('Failed to fetch metrics for node operator 7');

      expect(strip(wrapper).props('failure')).toBe('Failed to fetch metrics for node operator 7');
      expect(strip(wrapper).props('retryable')).toBe(true);
    });
  });
});
