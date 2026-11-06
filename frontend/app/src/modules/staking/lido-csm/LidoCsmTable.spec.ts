import type { LidoCsmNodeOperator, LidoCsmNodeOperatorPayload } from '@/modules/staking/staking-types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { type DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
  stakingModuleId: 3,
};

const WITHOUT_METRICS: LidoCsmNodeOperator = {
  address: '0x2222222222222222222222222222222222222222',
  metrics: null,
  nodeOperatorId: 3,
  stakingModuleId: 3,
};

const CSM_0X02_OPERATOR: LidoCsmNodeOperator = {
  address: '0x3333333333333333333333333333333333333333',
  metrics: null,
  nodeOperatorId: 4,
  stakingModuleId: 5,
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
              <div v-for="row in rows" :key="row.key" :data-testid="'row-' + row.key">
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

  function row(entry: LidoCsmNodeOperator): DOMWrapper<Element> {
    return wrapper.find(`[data-testid=row-${entry.address}-${entry.stakingModuleId}-${entry.nodeOperatorId}]`);
  }

  function amounts(entry: LidoCsmNodeOperator): (string | undefined)[] {
    const rowElement = row(entry).element;
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

      expect(amounts(WITH_METRICS)).toEqual(['2.5', '2', '0.5', '0.25']);
      expect(row(WITH_METRICS).find('[data-testid=cell-totalDeposited]').text()).toBe('7');
      expect(row(WITH_METRICS).find('[data-testid=lido-csm-node-operator-id]').text()).toBe('staking_page.lido_csm.modules.csm #12');
      expect(row(WITH_METRICS).find('[data-testid=lido-csm-operator-type]').text()).toBe('Permissionless');
    });

    it('should mark every metric unavailable for an operator without metrics', () => {
      wrapper = createWrapper([WITHOUT_METRICS]);

      expect(amounts(WITHOUT_METRICS)).toEqual([]);
      expect(row(WITHOUT_METRICS).find('[data-testid=lido-csm-operator-type]').exists()).toBe(false);
      for (const key of ['bondCurrent', 'bondRequired', 'bondClaimable', 'totalDeposited', 'rewardsPending'])
        expect(row(WITHOUT_METRICS).find(`[data-testid=cell-${key}]`).text()).toBe('staking_page.lido_csm.table.not_available');
    });

    it('should not warn about the bond of an operator that meets the requirement', () => {
      wrapper = createWrapper([WITH_METRICS]);

      expect(row(WITH_METRICS).find('[data-testid=lido-csm-bond-short]').exists()).toBe(false);
    });

    it('should warn about the bond of an under-bonded operator', () => {
      const short: LidoCsmNodeOperator = {
        ...WITH_METRICS,
        metrics: {
          bond: { claimable: bigNumberify('0'), current: bigNumberify('1.5'), required: bigNumberify('2') },
          keys: { totalDeposited: 7 },
          operatorType: { id: 1, label: 'Permissionless' },
          rewards: { pending: bigNumberify('0.25') },
        },
      };
      wrapper = createWrapper([short]);

      expect(row(WITH_METRICS).find('[data-testid=lido-csm-bond-short]').exists()).toBe(true);
    });
  });

  describe('remove', () => {
    it('should have each row\'s delete button ask about that operator first', () => {
      wrapper = createWrapper([WITH_METRICS, WITHOUT_METRICS]);

      expect(wrapper.findAllComponents(RowActions)[1].props('deleteConfirm')).toEqual({
        message: `staking_page.lido_csm.messages.confirm_delete_message::${WITHOUT_METRICS.address}, staking_page.lido_csm.modules.csm, 3`,
        title: 'staking_page.lido_csm.messages.confirm_delete_title',
      });
    });

    it('should remove the operator once the delete is confirmed, then ask for a reload', async () => {
      wrapper = createWrapper([WITH_METRICS, WITHOUT_METRICS]);

      await removeRow(1);
      await flushPromises();

      expect(spies.deleteNodeOperator).toHaveBeenCalledExactlyOnceWith({
        address: WITHOUT_METRICS.address,
        nodeOperatorId: 3,
        stakingModuleId: 3,
      });
      expect(wrapper.emitted('refresh')).toHaveLength(1);
    });

    it('should name the staking module of a CSM 0x02 operator and remove it from that module', async () => {
      wrapper = createWrapper([CSM_0X02_OPERATOR]);

      expect(row(CSM_0X02_OPERATOR).find('[data-testid=lido-csm-node-operator-id]').text()).toBe('staking_page.lido_csm.modules.csm_0x02 #4');

      await removeRow(0);
      await flushPromises();

      expect(spies.deleteNodeOperator).toHaveBeenCalledExactlyOnceWith({
        address: CSM_0X02_OPERATOR.address,
        nodeOperatorId: 4,
        stakingModuleId: 5,
      });
    });

    it('should list operators sharing an id and address in different modules as separate rows', () => {
      const sameIdInCsm0x02: LidoCsmNodeOperator = { ...WITHOUT_METRICS, stakingModuleId: 5 };
      wrapper = createWrapper([WITHOUT_METRICS, sameIdInCsm0x02]);

      expect(row(WITHOUT_METRICS).find('[data-testid=lido-csm-node-operator-id]').text()).toBe('staking_page.lido_csm.modules.csm #3');
      expect(row(sameIdInCsm0x02).find('[data-testid=lido-csm-node-operator-id]').text()).toBe('staking_page.lido_csm.modules.csm_0x02 #3');
    });

    it('should disable only the module row being removed when ids are shared across modules', async () => {
      spies.deleteNodeOperator.mockReturnValue(new Promise(() => {}));
      const sameIdInCsm0x02: LidoCsmNodeOperator = { ...WITHOUT_METRICS, stakingModuleId: 5 };
      wrapper = createWrapper([WITHOUT_METRICS, sameIdInCsm0x02]);

      await removeRow(1);

      expect(spies.deleteNodeOperator).toHaveBeenCalledExactlyOnceWith({
        address: WITHOUT_METRICS.address,
        nodeOperatorId: 3,
        stakingModuleId: 5,
      });
      expect(wrapper.findAllComponents(RowActions).map(action => action.props('disabled'))).toEqual([false, true]);
    });

    it('should disable only the row being removed until the removal settles', async () => {
      let resolve: (value: unknown) => void = () => {};
      spies.deleteNodeOperator.mockReturnValue(new Promise((done) => {
        resolve = done;
      }));
      wrapper = createWrapper([WITH_METRICS, WITHOUT_METRICS]);

      await removeRow(0);

      const actions = wrapper.findAllComponents(RowActions);
      expect(actions.map(action => action.props('disabled'))).toEqual([true, false]);

      resolve(true);
      await flushPromises();

      expect(wrapper.findAllComponents(RowActions).map(action => action.props('disabled'))).toEqual([false, false]);
    });

    it('should name a failed removal above the table, without a retry, and not reload', async () => {
      spies.deleteNodeOperator.mockRejectedValue(new Error('operator not tracked'));
      wrapper = createWrapper([WITH_METRICS]);

      await removeRow(0);
      await flushPromises();

      const strip = wrapper.find('[data-testid=lido-csm-delete-error]');
      expect(strip.text()).toContain('staking_page.lido_csm.messages.delete_failed');
      expect(strip.text()).toContain('operator not tracked');
      expect(strip.find('[data-testid=failure-strip-retry]').exists()).toBe(false);
      expect(wrapper.emitted('refresh')).toBeUndefined();
      expect(wrapper.findComponent(RowActions).props('disabled')).toBe(false);
    });
  });
});
