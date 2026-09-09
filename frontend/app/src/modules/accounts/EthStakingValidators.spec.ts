import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify, Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import EthStakingValidators from '@/modules/accounts/EthStakingValidators.vue';

const {
  accountOperation,
  confirmDelete,
  deleteSelected,
  editValidator,
  filters,
  modelSelected,
  refresh,
  rows,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    accountOperation: ref<boolean>(false),
    confirmDelete: vi.fn(),
    deleteSelected: vi.fn(),
    editValidator: vi.fn(),
    filters: ref<Record<string, unknown>>({}),
    modelSelected: ref<string[]>([]),
    refresh: vi.fn(),
    rows: ref<{ data: EthereumValidator[]; found: number; limit: number; total: number }>({
      data: [],
      found: 0,
      limit: 10,
      total: 0,
    }),
  };
});

vi.mock('@/modules/staking/eth/use-eth-validator-data', async () => {
  const { computed, ref } = await import('vue');
  return {
    useEthValidatorData: (): Record<string, unknown> => ({
      cols: computed(() => []),
      ethStakingValidators: computed(() => []),
      fields: computed(() => []),
      filters,
      modelSelected,
      pagination: ref({ limit: 10, page: 1, total: 0 }),
      rows: computed(() => rows.value),
      sort: ref([]),
    }),
  };
});

vi.mock('@/modules/staking/eth/use-eth-validator-operations', () => ({
  useEthValidatorOperations: (): Record<string, unknown> => ({
    accountOperation,
    confirmDelete,
    deleteSelected,
    edit: editValidator,
    refresh,
  }),
}));

vi.mock('@/modules/staking/eth/use-eth-validator-utils', async () => {
  const { computed } = await import('vue');
  return {
    useEthValidatorUtils: (): Record<string, unknown> => ({
      getOwnershipPercentage: (): string => '100',
      useTotal: () => computed(() => bigNumberify(0)),
      useTotalAmount: () => computed(() => bigNumberify(0)),
    }),
  };
});

vi.mock('@/modules/core/table/pill/composables/use-pill-bar-labels', () => ({
  usePillBarLabels: (): Record<string, unknown> => ({}),
}));

const ViewsMenuStub = defineComponent({
  emits: ['apply'],
  props: ['fields', 'location', 'state', 'disabled'],
  template: '<div />',
});

/** Renders the row actions, which is where a validator's edit and delete are wired. */
const TableStub = defineComponent({
  props: ['cols', 'rows', 'loading', 'sort', 'pagination', 'modelValue'],
  template: `<div>
    <template v-for="row in rows" :key="row.index">
      <slot name="item.actions" :row="row" />
    </template>
  </div>`,
});

const RowActionsStub = defineComponent({
  emits: ['edit-click', 'delete-click'],
  props: ['disabled', 'editTooltip'],
  template: '<div />',
});

function validator(index: number): EthereumValidator {
  return {
    amount: bigNumberify(32),
    index,
    ownershipPercentage: '100',
    publicKey: `0xabc${index}`,
    status: 'active',
    type: 'validator',
    value: bigNumberify(32),
  };
}

function createWrapper(): VueWrapper<any> {
  return mount(EthStakingValidators, {
    global: {
      stubs: {
        Eth2ValidatorLimitRow: true,
        PillFilterBar: { props: ['matches', 'fields', 'labels'], template: '<div><slot name="views" :disabled="false" /></div>' },
        PillViewsMenu: ViewsMenuStub,
        RowActions: RowActionsStub,
        RowAppend: true,
        RuiDataTable: TableStub,
      },
    },
  });
}

function deleteButton(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findAllComponents({ name: 'RuiButton' })[0];
}

describe('ethStakingValidators', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(accountOperation, false);
    set(filters, {});
    set(modelSelected, []);
    set(rows, { data: [validator(1), validator(2)], found: 2, limit: 10, total: 2 });
  });

  describe('deleting the selection', () => {
    it('should offer no delete while nothing is selected', () => {
      expect(deleteButton(createWrapper()).props('disabled')).toBe(true);
    });

    it('should offer it once validators are picked', async () => {
      const wrapper = createWrapper();

      set(modelSelected, ['1']);
      await nextTick();

      expect(deleteButton(wrapper).props('disabled')).toBe(false);
    });

    /** The selection is a list of keys, so the rows on screen are what resolves it. */
    it('should delete the picked validators out of the rows in view', async () => {
      const wrapper = createWrapper();
      set(modelSelected, ['1']);
      await nextTick();

      await deleteButton(wrapper).trigger('click');

      expect(deleteSelected).toHaveBeenCalledWith(get(rows).data, ['1']);
    });

    it('should let the selection be cleared', async () => {
      const wrapper = createWrapper();
      set(modelSelected, ['1']);
      await nextTick();

      const clear = wrapper.findAllComponents({ name: 'RuiButton' })[1];
      await clear.trigger('click');

      expect(get(modelSelected)).toEqual([]);
    });
  });

  /**
   * Every pill on this bar is filter-bound, so a saved view is its matches alone and the params
   * side stays empty rather than carrying a shape this table never reads.
   */
  describe('saved views', () => {
    it('should offer the current filters as the view to save', async () => {
      const wrapper = createWrapper();

      set(filters, { status: 'active' });
      await nextTick();

      expect(wrapper.findComponent(ViewsMenuStub).props('state')).toEqual({
        matches: { status: 'active' },
        params: {},
      });
    });

    it('should apply a saved view to the filters', async () => {
      const wrapper = createWrapper();

      wrapper.findComponent(ViewsMenuStub).vm.$emit('apply', { matches: { status: 'exited' }, params: {} });
      await nextTick();

      expect(get(filters)).toEqual({ status: 'exited' });
    });
  });

  describe('a validator row', () => {
    /** The parent opens the dialog, so the row has to hand it a state it can edit. */
    it('should hand the parent an edit state for the validator', async () => {
      editValidator.mockReturnValue({ chain: Blockchain.ETH2, data: {}, mode: 'edit', type: 'validator' });
      const wrapper = createWrapper();

      wrapper.findComponent(RowActionsStub).vm.$emit('edit-click');
      await nextTick();

      expect(editValidator).toHaveBeenCalledWith(validator(1));
      expect(wrapper.emitted('edit')?.at(-1)?.[0]).toEqual({
        chain: Blockchain.ETH2,
        data: {},
        mode: 'edit',
        type: 'validator',
      });
    });

    it('should confirm before deleting one', async () => {
      const wrapper = createWrapper();

      wrapper.findComponent(RowActionsStub).vm.$emit('delete-click');
      await nextTick();

      expect(confirmDelete).toHaveBeenCalledWith(validator(1));
    });

    /** A row cannot be acted on while another account operation is still running. */
    it('should close off the row while an operation is running', async () => {
      set(accountOperation, true);

      expect(createWrapper().findComponent(RowActionsStub).props('disabled')).toBe(true);
    });
  });

  it('should expose the refresh its parent drives', () => {
    createWrapper().vm.refresh();

    expect(refresh).toHaveBeenCalledTimes(1);
  });
});
