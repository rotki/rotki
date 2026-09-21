import type { LidoCsmNodeOperator, LidoCsmNodeOperatorPayload } from '@/modules/staking/staking-types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { type DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import LidoCsmTable from '@/modules/staking/lido-csm/LidoCsmTable.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    deleteNodeOperator: vi.fn<(payload: LidoCsmNodeOperatorPayload) => Promise<unknown>>(),
  },
}));

vi.mock('@/modules/staking/api/use-lido-csm-api', () => ({
  useLidoCsmApi: (): object => ({ deleteNodeOperator: spies.deleteNodeOperator }),
}));

const WITH_METRICS: LidoCsmNodeOperator = {
  address: '0x1111111111111111111111111111111111111111',
  metrics: {
    bond: { claimable: bigNumberify('0.5'), current: bigNumberify('2.5'), required: bigNumberify('2') },
    keys: { totalDeposited: 7 },
    operatorType: { id: 1, label: 'Permissionless' },
    rewards: { pending: bigNumberify('0.25') },
  },
  nodeOperatorId: 12,
};

const WITHOUT_METRICS: LidoCsmNodeOperator = {
  address: '0x2222222222222222222222222222222222222222',
  metrics: null,
  nodeOperatorId: 3,
};

describe('lidoCsmTable', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof LidoCsmTable>>;

  function createWrapper(rows: LidoCsmNodeOperator[]): VueWrapper<InstanceType<typeof LidoCsmTable>> {
    return mount(LidoCsmTable, {
      global: {
        plugins: [pinia],
        stubs: {
          BalanceDisplay: true,
          HashLink: true,
          RowActions: true,
          RuiDataTable: {
            props: ['rows', 'cols'],
            template: `<div>
              <div v-for="row in rows" :key="row.key" :data-testid="'row-' + row.nodeOperatorId">
                <div v-for="col in cols" :key="col.key" :data-testid="'cell-' + col.key">
                  <slot :name="'item.' + col.key" :row="row" />
                </div>
              </div>
            </div>`,
          },
        },
      },
      props: { loading: false, rows },
    });
  }

  function row(nodeOperatorId: number): DOMWrapper<Element> {
    return wrapper.find(`[data-testid=row-${nodeOperatorId}]`);
  }

  function amounts(nodeOperatorId: number): (string | undefined)[] {
    const rowElement = row(nodeOperatorId).element;
    return wrapper
      .findAllComponents(BalanceDisplay)
      .filter(display => rowElement.contains(display.element))
      .map(display => display.props('value')?.amount?.toFixed());
  }

  async function removeRow(index: number): Promise<void> {
    wrapper.findAllComponents(RowActions)[index].vm.$emit('delete-click');
    await nextTick();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createCustomPinia();
    setActivePinia(pinia);
    spies.deleteNodeOperator.mockResolvedValue(true);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('rows', () => {
    it('should show the bond, pending rewards and key count an operator reports', () => {
      wrapper = createWrapper([WITH_METRICS]);

      expect(amounts(12)).toEqual(['2.5', '2', '0.5', '0.25']);
      expect(row(12).find('[data-testid=cell-operatorTypeLabel]').text()).toBe('Permissionless');
      expect(row(12).find('[data-testid=cell-totalDeposited]').text()).toBe('7');
      expect(row(12).find('[data-testid=cell-nodeOperatorId]').text()).toBe('#12');
    });

    it('should mark every metric unavailable for an operator without metrics', () => {
      wrapper = createWrapper([WITHOUT_METRICS]);

      expect(amounts(3)).toEqual([]);
      for (const key of ['operatorTypeLabel', 'bondCurrent', 'bondRequired', 'bondClaimable', 'totalDeposited', 'rewardsPending'])
        expect(row(3).find(`[data-testid=cell-${key}]`).text()).toBe('staking_page.lido_csm.table.not_available');
    });
  });

  describe('remove', () => {
    it('should remove the operator only once confirmed, then ask for a reload', async () => {
      wrapper = createWrapper([WITH_METRICS, WITHOUT_METRICS]);

      await removeRow(1);

      expect(useConfirmStore().visible).toBe(true);
      expect(spies.deleteNodeOperator).not.toHaveBeenCalled();

      await useConfirmStore().confirm();
      await flushPromises();

      expect(spies.deleteNodeOperator).toHaveBeenCalledExactlyOnceWith({
        address: WITHOUT_METRICS.address,
        nodeOperatorId: 3,
      });
      expect(wrapper.emitted('refresh')).toHaveLength(1);
    });

    it('should keep the operator when the removal is dismissed', async () => {
      wrapper = createWrapper([WITH_METRICS]);

      await removeRow(0);
      await useConfirmStore().dismiss();
      await flushPromises();

      expect(spies.deleteNodeOperator).not.toHaveBeenCalled();
    });

    it('should disable only the row being removed until the removal settles', async () => {
      let resolve: (value: unknown) => void = () => {};
      spies.deleteNodeOperator.mockReturnValue(new Promise((done) => {
        resolve = done;
      }));
      wrapper = createWrapper([WITH_METRICS, WITHOUT_METRICS]);

      await removeRow(0);
      const confirming = useConfirmStore().confirm();
      await nextTick();

      const actions = wrapper.findAllComponents(RowActions);
      expect(actions.map(action => action.props('disabled'))).toEqual([true, false]);

      resolve(true);
      await confirming;
      await flushPromises();

      expect(wrapper.findAllComponents(RowActions).map(action => action.props('disabled'))).toEqual([false, false]);
    });

    it('should report a failed removal and not reload', async () => {
      spies.deleteNodeOperator.mockRejectedValue(new Error('operator not tracked'));
      wrapper = createWrapper([WITH_METRICS]);

      await removeRow(0);
      await useConfirmStore().confirm();
      await flushPromises();

      expect(useMessageStore().message).toMatchObject({
        description: 'staking_page.lido_csm.messages.delete_failed::operator not tracked',
        success: false,
      });
      expect(wrapper.emitted('refresh')).toBeUndefined();
      expect(wrapper.findComponent(RowActions).props('disabled')).toBe(false);
    });
  });
});
