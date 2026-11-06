import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import AccountingRuleFormDialog from '@/modules/settings/accounting/rule/AccountingRuleFormDialog.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    addAccountingRule: vi.fn<(rule: object) => Promise<boolean>>(),
    editAccountingRule: vi.fn<(rule: object) => Promise<boolean>>(),
    validate: vi.fn<() => boolean>(),
  },
}));

vi.mock('@/modules/settings/api/use-accounting-api', () => ({
  useAccountingApi: (): object => ({ addAccountingRule: spies.addAccountingRule, editAccountingRule: spies.editAccountingRule }),
}));

const FormStub = defineComponent({
  name: 'AccountingRuleForm',
  props: { errorMessages: { default: () => ({}), type: Object } },
  setup(_props, { expose }) {
    expose({ validate: spies.validate });
    return {};
  },
  template: '<div />',
});

const RULE: AccountingRuleEntry = {
  accountingTreatment: null,
  countCostBasisPnl: { value: false },
  countEntireAmountSpend: { value: false },
  counterparty: null,
  eventSubtype: 'fee',
  eventType: 'spend',
  identifier: 7,
  taxable: { value: false },
};

function createWrapper(editMode: boolean): VueWrapper<InstanceType<typeof AccountingRuleFormDialog>> {
  return mount(AccountingRuleFormDialog, {
    global: {
      stubs: {
        AccountingRuleForm: FormStub,
        BigDialog: {
          emits: ['confirm', 'cancel'],
          props: ['display', 'failure', 'failureTitle', 'loading', 'title'],
          template: '<div v-if="display"><slot /></div>',
        },
      },
    },
    props: { editMode, modelValue: { ...RULE } },
  });
}

async function save(wrapper: VueWrapper): Promise<void> {
  wrapper.findComponent(BigDialog).vm.$emit('confirm');
  await flushPromises();
}

describe('accountingRuleFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spies.validate.mockReturnValue(true);
    spies.addAccountingRule.mockResolvedValue(true);
    spies.editAccountingRule.mockResolvedValue(true);
  });

  it('should close and ask for a reload once saved', async () => {
    const wrapper = createWrapper(true);

    await save(wrapper);

    expect(spies.editAccountingRule).toHaveBeenCalledOnce();
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    expect(wrapper.emitted('refresh')).toHaveLength(1);
  });

  it('should hand field errors back to the form and name no failure', async () => {
    spies.addAccountingRule.mockRejectedValue(new ApiValidationError(JSON.stringify({ eventType: ['unknown type'] })));
    const wrapper = createWrapper(false);

    await save(wrapper);

    expect(wrapper.findComponent(FormStub).props('errorMessages')).toEqual({ eventType: ['unknown type'] });
    expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
  });

  it('should name any other failure in the dialog as an add error, and stay open', async () => {
    const error = new Error('database locked');
    spies.addAccountingRule.mockRejectedValue(error);
    const wrapper = createWrapper(false);

    await save(wrapper);

    const dialog = wrapper.findComponent(BigDialog);
    expect(dialog.props('failure')).toBe(error);
    expect(dialog.props('failureTitle')).toBe('accounting_settings.rule.add_error');
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should title a failed edit as an edit error', async () => {
    spies.editAccountingRule.mockRejectedValue(new Error('database locked'));
    const wrapper = createWrapper(true);

    await save(wrapper);

    expect(wrapper.findComponent(BigDialog).props('failureTitle')).toBe('accounting_settings.rule.edit_error');
  });

  it('should clear the failure when the next save starts', async () => {
    spies.addAccountingRule.mockRejectedValueOnce(new Error('database locked')).mockResolvedValueOnce(false);
    const wrapper = createWrapper(false);

    await save(wrapper);
    await save(wrapper);

    expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
  });
});
