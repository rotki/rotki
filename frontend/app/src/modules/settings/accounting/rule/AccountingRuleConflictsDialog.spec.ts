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

function conflict(remote: Partial<AccountingRule> = {}): AccountingRuleConflict {
  return { localData: rule(), localId: 1, remoteData: rule(remote) };
}

function createWrapper(): VueWrapper<any> {
  return mount(AccountingRuleConflictsDialog, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        BigDialog: BigDialogStub,
        // Globally stubbed to `true`, which would swallow the hint the dialog is choosing between.
        I18nT: { props: ['keypath'], template: '<span>{{ keypath }}<slot name="source" /></span>' },
      },
    },
  });
}

/** The table renders no column key onto the cell, so the columns are addressed by their order. */
const COLUMN_INDEX: Record<string, number> = {
  accountingTreatment: 6,
  countCostBasisPnl: 5,
  countEntireAmountSpend: 4,
  taxable: 3,
};

function cell(wrapper: VueWrapper<any>, key: string): DOMWrapper<Element> {
  return wrapper.findAll('tbody td')[COLUMN_INDEX[key]].find('div.w-full');
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
    it('should keep the local rules when the bulk choice is ticked', async () => {
      const wrapper = createWrapper();

      await wrapper.findComponent({ name: 'RuiCheckbox' }).vm.$emit('update:modelValue', true);

      expect(get(modelSolveAllUsing)).toBe('local');
    });

    it('should return to per-conflict choices when it is unticked', async () => {
      set(modelSolveAllUsing, 'remote');
      const wrapper = createWrapper();

      await wrapper.findComponent({ name: 'RuiCheckbox' }).vm.$emit('update:modelValue', false);

      expect(get(modelSolveAllUsing)).toBeUndefined();
    });

    it('should count what is left to answer while choosing one at a time', () => {
      set(collection, { data: [conflict()], found: 1, limit: 10, total: 3 });

      const hint = createWrapper().find('.text-caption');

      expect(hint.text()).toContain('conflict_dialog.hint');
    });

    it('should say which side it is taking once the bulk choice is made', () => {
      set(modelSolveAllUsing, 'remote');

      const hint = createWrapper().find('.text-caption');

      expect(hint.text()).toContain('conflict_dialog.resolve_all_hint');
    });
  });

  /**
   * Each column is highlighted only where the two versions disagree, so the user can see what the
   * update would change without reading every row.
   */
  describe('highlighting the differences', () => {
    const highlight = 'bg-rui-error-lighter/[0.1]';

    beforeEach(() => {
      set(modelSolveAllUsing, 'local');
    });

    it('should highlight nothing when the two versions agree', () => {
      set(collection, { data: [conflict()], found: 1, limit: 10, total: 1 });

      const wrapper = createWrapper();

      expect(cell(wrapper, 'taxable').classes()).not.toContain(highlight);
      expect(cell(wrapper, 'countEntireAmountSpend').classes()).not.toContain(highlight);
      expect(cell(wrapper, 'countCostBasisPnl').classes()).not.toContain(highlight);
    });

    it('should highlight the taxable column when only it differs', () => {
      set(collection, { data: [conflict({ taxable: property(false) })], found: 1, limit: 10, total: 1 });

      const wrapper = createWrapper();

      expect(cell(wrapper, 'taxable').classes()).toContain(highlight);
      expect(cell(wrapper, 'countEntireAmountSpend').classes()).not.toContain(highlight);
    });

    it('should highlight the spend column when only it differs', () => {
      set(collection, {
        data: [conflict({ countEntireAmountSpend: property(false) })],
        found: 1,
        limit: 10,
        total: 1,
      });

      const wrapper = createWrapper();

      expect(cell(wrapper, 'countEntireAmountSpend').classes()).toContain(highlight);
      expect(cell(wrapper, 'taxable').classes()).not.toContain(highlight);
    });

    it('should highlight the cost basis column when only it differs', () => {
      set(collection, { data: [conflict({ countCostBasisPnl: property(false) })], found: 1, limit: 10, total: 1 });

      const wrapper = createWrapper();

      expect(cell(wrapper, 'countCostBasisPnl').classes()).toContain(highlight);
      expect(cell(wrapper, 'taxable').classes()).not.toContain(highlight);
    });

    it('should highlight the treatment column when only it differs', () => {
      set(collection, { data: [conflict({ accountingTreatment: AccountingTreatment.SWAP })], found: 1, limit: 10, total: 1 });

      const wrapper = createWrapper();

      expect(cell(wrapper, 'accountingTreatment').classes()).toContain(highlight);
    });
  });
});
