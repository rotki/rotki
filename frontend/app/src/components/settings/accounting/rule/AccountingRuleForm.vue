<script setup lang="ts">
import { required } from '@vuelidate/validators';
import { omit } from 'lodash-es';
import {
  AccountingMethod,
  type AccountingRuleEntry,
  AccountingTreatment
} from '@/types/settings/accounting';
import { toMessages } from '@/utils/validation';
import { ApiValidationError } from '@/types/api/errors';

const props = withDefaults(
  defineProps<{
    editableItem?: AccountingRuleEntry | null;
  }>(),
  {
    editableItem: null
  }
);

const { editableItem } = toRefs(props);

const getPlaceholderRule = (): AccountingRuleEntry => ({
  identifier: -1,
  eventType: '',
  eventSubtype: '',
  counterparty: '',
  taxable: false,
  countEntireAmountSpend: false,
  countCostBasisPnl: false,
  method: AccountingMethod.SPEND,
  accountingTreatment: AccountingTreatment.SWAP
});

const state: Ref<AccountingRuleEntry> = ref(getPlaceholderRule());

const rules = {
  eventType: { required },
  eventSubtype: { required },
  counterparty: { externalServerValidation: () => true },
  method: { required },
  accountingTreatment: { required }
};

const { t } = useI18n();

const { setValidation, setSubmitFunc } = useAccountingRuleForm();

const errorMessages = ref<Record<string, string[] | string>>({});

const v$ = setValidation(rules, state, {
  $autoDirty: true,
  $externalResults: errorMessages
});

onMounted(() => {
  const editable = get(editableItem);
  if (editable) {
    reset(editable);
  }
});

watch(editableItem, editableItem => {
  if (editableItem) {
    reset(editableItem);
  }
});

const reset = (newState?: AccountingRuleEntry) => {
  set(state, newState ?? getPlaceholderRule());
};

const { addAccountingRule, editAccountingRule } = useAccountingApi();
const { setMessage } = useMessageStore();

const save = async () => {
  const editing = !!get(editableItem);
  const payload = get(state);

  try {
    const result = editing
      ? await editAccountingRule(payload)
      : await addAccountingRule(omit(payload, 'identifier'));

    if (result) {
      reset();
    }

    return result;
  } catch (e: any) {
    const errorTitle = editing
      ? t('accounting_settings.rule.edit_error')
      : t('accounting_settings.rule.add_error');

    if (e instanceof ApiValidationError) {
      const messages = e.errors;

      set(errorMessages, messages);

      const keys = Object.keys(messages);
      const knownKeys = Object.keys(payload);
      const unknownKeys = keys.filter(key => !knownKeys.includes(key));

      if (unknownKeys.length > 0) {
        setMessage({
          title: errorTitle,
          description: unknownKeys
            .map(key => `${key}: ${messages[key]}`)
            .join(', '),
          success: false
        });
      }
    } else {
      setMessage({
        title: errorTitle,
        description: e.message,
        success: false
      });
    }

    return false;
  }
};

setSubmitFunc(save);

const { historyEventTypesData, historyEventSubTypesData, counterparties } =
  useHistoryEventMappings();

const accountingMethods = Object.values(AccountingMethod).map(identifier => ({
  identifier,
  label: toSentenceCase(identifier)
}));

const accountingTreatments = Object.values(AccountingTreatment).map(
  identifier => ({
    identifier,
    label: toSentenceCase(identifier)
  })
);
</script>

<template>
  <form class="pt-2">
    <div class="grid grid-cols-3 gap-4">
      <VAutocomplete
        v-model="state.eventType"
        outlined
        required
        :label="t('accounting_settings.rule.labels.event_type')"
        :items="historyEventTypesData"
        item-value="identifier"
        item-text="label"
        :error-messages="toMessages(v$.eventType)"
        @blur="v$.eventType.$touch()"
      />
      <VAutocomplete
        v-model="state.eventSubtype"
        outlined
        required
        :label="t('accounting_settings.rule.labels.event_subtype')"
        :items="historyEventSubTypesData"
        item-value="identifier"
        item-text="label"
        :error-messages="toMessages(v$.eventSubtype)"
        @blur="v$.eventSubtype.$touch()"
      />
      <ComboboxWithCustomInput
        v-model="state.counterparty"
        outlined
        required
        clearable
        auto-select-first
        :label="t('accounting_settings.rule.labels.counterparty')"
        :items="counterparties"
        :error-messages="toMessages(v$.counterparty)"
        @blur="v$.counterparty.$touch()"
      />
    </div>
    <div class="border-t py-2" />
    <div>
      <RuiCheckbox v-model="state.taxable" color="primary">
        {{ t('accounting_settings.rule.labels.taxable') }}
        <div class="text-rui-text-secondary text-body-2">
          {{ t('accounting_settings.rule.labels.taxable_subtitle') }}
        </div>
      </RuiCheckbox>
      <RuiCheckbox v-model="state.countEntireAmountSpend" color="primary">
        {{ t('accounting_settings.rule.labels.count_entire_amount_spend') }}
        <div class="text-rui-text-secondary text-body-2">
          {{
            t(
              'accounting_settings.rule.labels.count_entire_amount_spend_subtitle'
            )
          }}
        </div>
      </RuiCheckbox>
      <RuiCheckbox v-model="state.countCostBasisPnl" color="primary">
        {{ t('accounting_settings.rule.labels.count_cost_basis_pnl') }}
        <div class="text-rui-text-secondary text-body-2">
          {{
            t('accounting_settings.rule.labels.count_cost_basis_pnl_subtitle')
          }}
        </div>
      </RuiCheckbox>
    </div>
    <div class="grid grid-cols-2 gap-4 pt-4">
      <VSelect
        v-model="state.method"
        outlined
        :items="accountingMethods"
        item-value="identifier"
        item-text="label"
        :label="t('accounting_settings.rule.labels.method')"
        :error-messages="toMessages(v$.method)"
        @blur="v$.method.$touch()"
      />
      <VSelect
        v-model="state.accountingTreatment"
        outlined
        :items="accountingTreatments"
        item-value="identifier"
        item-text="label"
        :label="t('accounting_settings.rule.labels.accounting_treatment')"
        :error-messages="toMessages(v$.accountingTreatment)"
        @blur="v$.accountingTreatment.$touch()"
      />
    </div>
  </form>
</template>
