import type { EditableMissingPrice, Report } from '@/modules/reports/report-types';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, markRaw } from 'vue';
import ReportActionableCard from '@/modules/reports/ReportActionableCard.vue';

const FILLED: EditableMissingPrice = {
  fromAsset: 'ETH',
  price: '10',
  saved: false,
  time: 1,
  toAsset: 'EUR',
  useRefreshedHistoricalPrice: false,
};

const PricesStub = markRaw(defineComponent({
  name: 'PricesStub',
  setup: (_props, { slots }) => (): unknown => h('div', slots.actions?.({ items: [FILLED] })),
}));

const { unpin } = vi.hoisted(() => ({ unpin: vi.fn<() => void>() }));

vi.mock('@/modules/reports/use-reports-store', async () => {
  const { reactive, ref } = await import('vue');
  return { useReportsStore: (): object => reactive({ actionableItems: ref(undefined) }) };
});

vi.mock('@/modules/shell/pinned/use-pinned-panel', () => ({
  usePinnedPanel: (): object => ({ pin: vi.fn(), unpin }),
}));

vi.mock('@/modules/reports/use-report-actionable-items', async (importOriginal) => {
  const { computed, shallowRef } = await import('vue');
  return {
    ...await importOriginal<object>(),
    useReportActionableStepper: (): object => ({
      counts: computed(() => ({ missingAcquisitionsLength: 0, missingPricesLength: 1, total: 1 })),
      modelStep: shallowRef<number>(1),
      steps: computed(() => [{ hint: '', items: [], key: 'missingPrices', selector: PricesStub, title: '' }]),
    }),
  };
});

describe('reportActionableCard', () => {
  function createWrapper(): VueWrapper<InstanceType<typeof ReportActionableCard>> {
    return mount(ReportActionableCard, {
      global: { stubs: { RuiStepper: true } },
      props: { report: createMock<Report>({}) },
    });
  }

  async function finish(wrapper: VueWrapper): Promise<void> {
    const button = wrapper.findAll('button').find(item => item.text() === 'common.actions.finish');
    await button?.trigger('click');
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show the finish summary in the card, in place of the step actions', async () => {
    const wrapper = createWrapper();

    await finish(wrapper);

    const summary = wrapper.find('[data-testid=report-actionable-finish]');
    expect(summary.text()).toContain('profit_loss_report.actionable.missing_prices.all_prices_filled');
    expect(wrapper.findAll('button').some(item => item.text() === 'common.actions.finish')).toBe(false);
    expect(wrapper.emitted('regenerate')).toBeUndefined();
  });

  it('should ask for the report to be regenerated once the summary is accepted', async () => {
    const wrapper = createWrapper();
    await finish(wrapper);

    await wrapper.find('[data-testid=report-actionable-finish] [data-testid=inline-confirm-accept]').trigger('click');

    expect(wrapper.emitted('regenerate')).toHaveLength(1);
    expect(wrapper.find('[data-testid=report-actionable-finish]').exists()).toBe(false);
  });

  it('should go back to the step actions when the summary is cancelled', async () => {
    const wrapper = createWrapper();
    await finish(wrapper);

    await wrapper.find('[data-testid=report-actionable-finish] [data-testid=inline-confirm-cancel]').trigger('click');

    expect(wrapper.emitted('regenerate')).toBeUndefined();
    expect(wrapper.findAll('button').some(item => item.text() === 'common.actions.finish')).toBe(true);
  });
});
