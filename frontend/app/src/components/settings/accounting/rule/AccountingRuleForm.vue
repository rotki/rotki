<script setup lang="ts">
import { required } from '@vuelidate/validators';
import { omit } from 'lodash-es';
import {
  type AccountingRuleEntry,
  AccountingTreatment,
} from '@/types/settings/accounting';
import { toMessages } from '@/utils/validation';
import { ApiValidationError } from '@/types/api/errors';

const props = withDefaults(
  defineProps<{
    editableItem?: AccountingRuleEntry | null;
  }>(),
  {
    editableItem: null,
  },
);

const { editableItem } = toRefs(props);

const state: Ref<AccountingRuleEntry> = ref(getPlaceholderRule());

const externalServerValidation = () => true;

const rules = {
  eventType: { required },
  eventSubtype: { required },
  counterparty: { externalServerValidation },
  accountingTreatment: { externalServerValidation },
};

const { t } = useI18n();

const { setValidation, setSubmitFunc } = useAccountingRuleForm();

const errorMessages = ref<Record<string, string[] | string>>({});

const v$ = setValidation(rules, state, {
  $autoDirty: true,
  $externalResults: errorMessages,
});

onMounted(() => {
  const editable = get(editableItem);
  if (editable)
    reset(editable);
});

watch(editableItem, (editableItem) => {
  if (editableItem)
    reset(editableItem);
});

function reset(newState?: AccountingRuleEntry) {
  if (newState)
    set(state, { ...newState });
  else
    set(state, getPlaceholderRule());
}

const { addAccountingRule, editAccountingRule } = useAccountingApi();
const { setMessage } = useMessageStore();

async function save() {
  const editing = Number(get(editableItem)?.identifier) > 0;
  const stateVal = get(state);

  const payload = {
    ...stateVal,
    counterparty: stateVal.counterparty || null,
  };

  try {
    const result = editing
      ? await editAccountingRule(payload)
      : await addAccountingRule(omit(payload, 'identifier'));

    if (result)
      reset();

    return result;
  }
  catch (error: any) {
    const errorTitle = editing
      ? t('accounting_settings.rule.edit_error')
      : t('accounting_settings.rule.add_error');

    let errors = error.message;
    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(payload);

    if (typeof errors === 'string') {
      setMessage({
        title: errorTitle,
        description: errors,
        success: false,
      });
    }
    else {
      set(errorMessages, errors);
    }

    return false;
  }
}

setSubmitFunc(save);

const accountingTreatments = Object.values(AccountingTreatment).map(
  identifier => ({
    identifier,
    label: toSentenceCase(identifier),
  }),
);
</script>

<template>
  <form>
    <HistoryEventTypeForm
      :event-type.sync="state.eventType"
      :event-subtype.sync="state.eventSubtype"
      :counterparty="state.counterparty"
      :v$="v$"
      disable-warning
    />

    <CounterpartyInput
      v-model="state.counterparty"
      class="md:w-1/2"
      :label="t('common.counterparty')"
      :error-messages="toMessages(v$.counterparty)"
      @blur="v$.counterparty.$touch()"
    />

    <AccountingRuleWithLinkedSetting
      v-model="state.taxable"
      class="border-t border-default"
      identifier="taxable"
      :label="t('accounting_settings.rule.labels.taxable')"
      :hint="t('accounting_settings.rule.labels.taxable_subtitle')"
    />

    <AccountingRuleWithLinkedSetting
      v-model="state.countEntireAmountSpend"
      class="border-t border-default"
      identifier="countEntireAmountSpend"
      :label="t('accounting_settings.rule.labels.count_entire_amount_spend')"
      :hint="
        t('accounting_settings.rule.labels.count_entire_amount_spend_subtitle')
      "
    />

    <AccountingRuleWithLinkedSetting
      v-model="state.countCostBasisPnl"
      class="border-t border-default"
      identifier="countCostBasisPnl"
      :label="t('accounting_settings.rule.labels.count_cost_basis_pnl')"
      :hint="t('accounting_settings.rule.labels.count_cost_basis_pnl_subtitle')"
    />

    <RuiDivider class="mb-6" />

    <VAutocomplete
      v-model="state.accountingTreatment"
      class="md:w-1/2"
      outlined
      :items="accountingTreatments"
      item-value="identifier"
      item-text="label"
      clearable
      :label="t('accounting_settings.rule.labels.accounting_treatment')"
      :error-messages="toMessages(v$.accountingTreatment)"
      @blur="v$.accountingTreatment.$touch()"
    />
  </form>
</template>
