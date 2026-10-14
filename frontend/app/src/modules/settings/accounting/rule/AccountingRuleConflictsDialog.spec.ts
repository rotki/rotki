import type { ConflictResolutionStrategy } from '@/modules/core/common/common-types';
import type { useAccountingRuleConflictResolution } from '@/modules/settings/accounting/rule/use-accounting-rule-conflict-resolution';
import { type DOMWrapper, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, nextTick, ref } from 'vue';
import AccountingRuleConflictsDialog from '@/modules/settings/accounting/rule/AccountingRuleConflictsDialog.vue';
import { type AccountingRule, type AccountingRuleConflict, AccountingTreatment } from '@/modules/settings/types/accounting';
import { createRuiPlugin } from '@/plugins/rui';

const { collection, modelResolution, modelSolveAllUsing, onResolved, refetch, save } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    collection: ref<{ data: AccountingRuleConflict[]; found: number; limit: number; total: number }>({
      data: [],
      found: 0,
      limit: 10,
      total: 0,
    }),
    modelResolution: ref<Record<string, ConflictResolutionStrategy>>({}),
    modelSolveAllUsing: ref<ConflictResolutionStrategy | undefined>(),
    onResolved: { call: (): void => {} },
    refetch: vi.fn(async () => {}),
    save: vi.fn(async () => {}),
  };
});

vi.mock('@/modules/settings/accounting/rule/use-accounting-rule-conflict-resolution', () => ({
  useAccountingRuleConflictResolution: (
    options: { onResolved: () => void },
  ): ReturnType<typeof useAccountingRuleConflictResolution> => {
    onResolved.call = options.onResolved;
    return {
      collection,
      error: ref(undefined),
      isLoading: ref(false),
      loading: ref(false),
      modelResolution,
      modelSolveAllUsing,
      pagination: computed({ get: () => ({ limit: 10, page: 1, total: 0 }), set: () => {} }),
      refetch,
      remaining: computed(() => collection.value.total - Object.keys(modelResolution.value).length),
      resolutionLength: computed(() => Object.keys(modelResolution.value).length),
      save,
      valid: computed(() => !!modelSolveAllUsing.value || Object.keys(modelResolution.value).length > 0),
    };
  },
}));

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): Record<string, (value: string) => unknown> => ({
    getEventTypeData: () => ({ color: 'success', icon: 'lu-arrow-down', label: 'Receive' }),
    getHistoryEventSubTypeName: (subtype: string) => subtype,
    getHistoryEventTypeName: (type: string) => type,
  }),
}));

vi.mock('@/modules/settings/accounting/use-accounting-rule-mappings', () => ({
  useAccountingRuleMappings: (): { accountingRuleLinkedMappingData: () => Ref<never[]> } => ({
    accountingRuleLinkedMappingData: () => ref([]),
  }),
}));

/** `BigDialog` teleports and owns the footer buttons; the two here stand for confirm and cancel. */
const BigDialogStub = {
  emits: ['confirm', 'cancel'],
  name: 'BigDialog',
  props: ['title', 'display', 'action', 'loading', 'layout', 'persistent'],
  template: `<div>
    <slot />
    <button data-testid="stub-confirm" @click="$emit('confirm')" />
    <button data-testid="stub-cancel" @click="$emit('cancel')" />
  </div>`,
};

function property(value: boolean): { value: boolean } {
  return { value };
}

function rule(overrides: Partial<AccountingRule> = {}): AccountingRule {
  return {
    accountingTreatment: null,
    counterparty: null,
    countCostBasisPnl: property(true),
    countEntireAmountSpend: property(true),
    eventSubtype: 'receive',
    eventType: 'receive',
    taxable: property(true),
    ...overrides,
  };
}

function conflict(remote: Partial<AccountingRule> = {}, localId = 1): AccountingRuleConflict {
  return { localData: rule(), localId, remoteData: rule(remote) };
}

function createWrapper(): VueWrapper<any> {
  return mount(AccountingRuleConflictsDialog, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        BigDialog: BigDialogStub,
      },
    },
  });
}

/** The header label of each property column, which the test i18n renders as its key. */
const COLUMN_LABEL: Record<string, string> = {
  accountingTreatment: 'accounting_settings.rule.labels.accounting_treatment',
  countCostBasisPnl: 'accounting_settings.rule.labels.count_cost_basis_pnl',
  countEntireAmountSpend: 'accounting_settings.rule.labels.count_entire_amount_spend',
  taxable: 'accounting_settings.rule.labels.taxable',
};

function headerTexts(wrapper: VueWrapper<any>): string[] {
  return wrapper.findAll('thead th').map(th => th.text());
}

/** The bulk choice is the first button group; the per-row ones follow in the table. */
function strategyGroup(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent({ name: 'RuiButtonGroup' });
}

function summary(wrapper: VueWrapper<any>): string {
  return wrapper.find('[data-testid=accounting-rule-conflicts-summary]').text();
}

/** Columns come and go with the data, so a property's cell is found through its header. */
function cell(wrapper: VueWrapper<any>, key: string, row = 0): DOMWrapper<Element> {
  const index = headerTexts(wrapper).findIndex(text => text.includes(COLUMN_LABEL[key]));
  expect(index, `no column for ${key}`).toBeGreaterThanOrEqual(0);
  return wrapper.findAll('tbody tr')[row].findAll('td')[index].find('div.w-full');
}

describe('accountingRuleConflictsDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(collection, { data: [], found: 0, limit: 10, total: 0 });
    set(modelResolution, {});
    set(modelSolveAllUsing, undefined);
  });

  it('should read the first page of conflicts when it opens', () => {
    createWrapper();

    expect(refetch).toHaveBeenCalledTimes(1);
  });

  describe('submitting', () => {
    it('should refuse to save while nothing has been chosen', () => {
      const wrapper = createWrapper();

      expect(wrapper.findComponent(BigDialogStub).props('action')).toMatchObject({ disabled: true });
    });

    it('should allow saving once a strategy is chosen', async () => {
      const wrapper = createWrapper();

      set(modelSolveAllUsing, 'local');
      await nextTick();

      expect(wrapper.findComponent(BigDialogStub).props('action')).toMatchObject({ disabled: false });
    });

    it('should submit the resolution on confirm', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=stub-confirm]').trigger('click');

      expect(save).toHaveBeenCalledTimes(1);
    });

    it('should close on cancel without submitting', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=stub-cancel]').trigger('click');

      expect(wrapper.emitted('close')).toHaveLength(1);
      expect(save).not.toHaveBeenCalled();
    });

    it('should refresh the rules and close once every conflict is resolved', () => {
      const wrapper = createWrapper();

      onResolved.call();

      expect(wrapper.emitted('refresh')).toHaveLength(1);
      expect(wrapper.emitted('close')).toHaveLength(1);
    });

    /** Choices made one conflict at a time are lost on a stray click outside the dialog. */
    it('should refuse to be dismissed by accident once choices have been made', async () => {
      const wrapper = createWrapper();

      expect(wrapper.findComponent(BigDialogStub).props('persistent')).toBe(false);

      set(modelResolution, { 1: 'local' });
      await nextTick();

      expect(wrapper.findComponent(BigDialogStub).props('persistent')).toBe(true);
    });
  });

  describe('resolving everything at once', () => {
    it('should start out choosing per rule', () => {
      const wrapper = createWrapper();

      expect(strategyGroup(wrapper).props('modelValue')).toBe('per_rule');
    });

    it('should keep every local rule once that is chosen', async () => {
      const wrapper = createWrapper();

      await strategyGroup(wrapper).vm.$emit('update:modelValue', 'local');

      expect(get(modelSolveAllUsing)).toBe('local');
    });

    it('should return to per-rule choices', async () => {
      set(modelSolveAllUsing, 'remote');
      const wrapper = createWrapper();

      await strategyGroup(wrapper).vm.$emit('update:modelValue', 'per_rule');

      expect(get(modelSolveAllUsing)).toBeUndefined();
    });

    it('should count what is left to answer while choosing one at a time', () => {
      set(collection, { data: [conflict()], found: 1, limit: 10, total: 3 });

      expect(summary(createWrapper())).toContain('accounting_settings.rule.conflicts.summary.remaining');
    });

    it('should say which side it is taking once the bulk choice is made', () => {
      set(modelSolveAllUsing, 'remote');

      expect(summary(createWrapper())).toContain('accounting_settings.rule.conflicts.summary.all_remote');
    });
  });

  describe('showing the outcome', () => {
    it('should fade the version a row will not keep', async () => {
      set(collection, { data: [conflict({ taxable: property(false) })], found: 1, limit: 10, total: 1 });
      const wrapper = createWrapper();

      set(modelResolution, { 1: 'remote' });
      await nextTick();

      const [local, remote] = cell(wrapper, 'taxable').findAll(':scope > div');
      expect(local.classes()).toContain('opacity-40');
      expect(remote.classes()).not.toContain('opacity-40');
    });

    it('should fade nothing before a version is chosen', () => {
      set(collection, { data: [conflict({ taxable: property(false) })], found: 1, limit: 10, total: 1 });

      const rows = cell(createWrapper(), 'taxable').findAll(':scope > div');

      expect(rows.every(row => !row.classes().includes('opacity-40'))).toBe(true);
    });
  });

  /**
   * Each column is highlighted only where the two versions disagree, so the user can see what the
   * update would change without reading every row.
   */
  describe('highlighting the differences', () => {
    const highlight = 'bg-rui-warning/10';

    it('should tint a cell only on the row that disagrees there', () => {
      set(collection, {
        data: [conflict({ taxable: property(false) }, 1), conflict({ countEntireAmountSpend: property(false) }, 2)],
        found: 2,
        limit: 10,
        total: 2,
      });

      const wrapper = createWrapper();

      expect(cell(wrapper, 'taxable', 0).classes()).toContain(highlight);
      expect(cell(wrapper, 'taxable', 1).classes()).not.toContain(highlight);
      expect(cell(wrapper, 'countEntireAmountSpend', 0).classes()).not.toContain(highlight);
      expect(cell(wrapper, 'countEntireAmountSpend', 1).classes()).toContain(highlight);
    });

    it('should tint the treatment when only it differs', () => {
      set(collection, { data: [conflict({ accountingTreatment: AccountingTreatment.SWAP })], found: 1, limit: 10, total: 1 });

      expect(cell(createWrapper(), 'accountingTreatment').classes()).toContain(highlight);
    });
  });

  /** A property no conflict disagrees on cannot be what the choice is about, so its column steps aside. */
  describe('leaving out what agrees', () => {
    it('should show only the properties some conflict disagrees on', () => {
      set(collection, { data: [conflict({ taxable: property(false) })], found: 1, limit: 10, total: 1 });

      const headers = headerTexts(createWrapper()).join(' ');

      expect(headers).toContain(COLUMN_LABEL.taxable);
      expect(headers).not.toContain(COLUMN_LABEL.countEntireAmountSpend);
      expect(headers).not.toContain(COLUMN_LABEL.countCostBasisPnl);
      expect(headers).not.toContain(COLUMN_LABEL.accountingTreatment);
    });

    it('should name the left-out properties under the table', () => {
      set(collection, { data: [conflict({ taxable: property(false) })], found: 1, limit: 10, total: 1 });

      const note = createWrapper().find('[data-testid=accounting-rule-conflicts-matching]');

      expect(note.exists()).toBe(true);
      expect(note.text()).toContain('accounting_settings.rule.conflicts.matching');
    });

    it('should keep a column whose versions follow different settings', () => {
      set(collection, {
        data: [conflict({ taxable: { linkedSetting: 'include_gas_costs', value: true } })],
        found: 1,
        limit: 10,
        total: 1,
      });

      expect(headerTexts(createWrapper()).join(' ')).toContain(COLUMN_LABEL.taxable);
    });

    it('should show every column and no note while nothing is loaded', () => {
      const wrapper = createWrapper();
      const headers = headerTexts(wrapper).join(' ');

      for (const label of Object.values(COLUMN_LABEL))
        expect(headers).toContain(label);
      expect(wrapper.find('[data-testid=accounting-rule-conflicts-matching]').exists()).toBe(false);
    });
  });

  describe('the choices', () => {
    it('should drop the per-rule buttons once a bulk choice decides every row', () => {
      set(collection, { data: [conflict({ taxable: property(false) })], found: 1, limit: 10, total: 1 });
      set(modelSolveAllUsing, 'remote');

      const headers = headerTexts(createWrapper()).join(' ');

      expect(headers).not.toContain('accounting_settings.rule.conflicts.labels.choose_version');
    });

    it('should say Save writes only the choices made so far', () => {
      set(modelResolution, { 1: 'local' });

      const action = createWrapper().findComponent(BigDialogStub).props('action');

      expect(action.primary).toContain('accounting_settings.rule.conflicts.save.choices');
    });

    it('should say Save settles every conflict under a bulk choice', () => {
      set(modelSolveAllUsing, 'local');

      const action = createWrapper().findComponent(BigDialogStub).props('action');

      expect(action.primary).toContain('accounting_settings.rule.conflicts.save.all');
    });
  });
});
