<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import { toSentenceCase } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';
import AccountingRuleWithLinkedSetting from '@/components/settings/accounting/rule/AccountingRuleWithLinkedSetting.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import { type AccountingRuleEntry, AccountingTreatment } from '@/types/settings/accounting';
import { refOptional, useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<AccountingRuleEntry>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<{
  eventIds?: number[];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  historyEventSubTypesData,
  historyEventTypesData,
} = useHistoryEventMappings();

const counterparty = refOptional(useRefPropVModel(modelValue, 'counterparty'), '');
const accountingTreatment = useRefPropVModel(modelValue, 'accountingTreatment');
const eventType = useRefPropVModel(modelValue, 'eventType');
const eventSubtype = useRefPropVModel(modelValue, 'eventSubtype');
const taxable = useRefPropVModel(modelValue, 'taxable');
const countEntireAmountSpend = useRefPropVModel(modelValue, 'countEntireAmountSpend');
const countCostBasisPnl = useRefPropVModel(modelValue, 'countCostBasisPnl');

const externalServerValidation = () => true;

const rules = {
  accountingTreatment: { externalServerValidation },
  counterparty: { externalServerValidation },
  eventSubtype: { required },
  eventType: { required },
};

const states = {
  accountingTreatment,
  counterparty,
  eventSubtype,
  eventType,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errors,
  },
);

useFormStateWatcher(states, stateUpdated);

// When eventIds are present, automatically set first values
watchEffect(() => {
  if (props.eventIds && props.eventIds.length > 0) {
    const eventTypes = get(historyEventTypesData);

    // Set first event type if not set
    if (!get(eventType) && eventTypes.length > 0) {
      set(eventType, eventTypes[0].identifier);
    }

    // Set first event subtype if not set
    if (!get(eventSubtype)) {
      const subtypes = get(historyEventSubTypesData);
      if (subtypes.length > 0) {
        set(eventSubtype, subtypes[0].identifier);
      }
    }
  }
});

const accountingTreatments = Object.values(AccountingTreatment).map(identifier => ({
  identifier,
  label: toSentenceCase(identifier),
}));

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <form>
    <template v-if="!eventIds || eventIds.length === 0">
      <HistoryEventTypeForm
        v-model:event-type="eventType"
        v-model:event-subtype="eventSubtype"
        :counterparty="counterparty"
        :v$="v$"
        disable-warning
      />

      <CounterpartyInput
        v-model="counterparty"
        class="md:w-1/2"
        :label="t('common.counterparty')"
        :error-messages="toMessages(v$.counterparty)"
        @blur="v$.counterparty.$touch()"
      />
    </template>

    <AccountingRuleWithLinkedSetting
      v-model="taxable"
      class="border-t border-default"
      identifier="taxable"
      :label="t('accounting_settings.rule.labels.taxable')"
      :hint="t('accounting_settings.rule.labels.taxable_subtitle')"
    />

    <AccountingRuleWithLinkedSetting
      v-model="countEntireAmountSpend"
      class="border-t border-default"
      identifier="countEntireAmountSpend"
      :label="t('accounting_settings.rule.labels.count_entire_amount_spend')"
      :hint="t('accounting_settings.rule.labels.count_entire_amount_spend_subtitle')"
    />

    <AccountingRuleWithLinkedSetting
      v-model="countCostBasisPnl"
      class="border-t border-default"
      identifier="countCostBasisPnl"
      :label="t('accounting_settings.rule.labels.count_cost_basis_pnl')"
      :hint="t('accounting_settings.rule.labels.count_cost_basis_pnl_subtitle')"
    />

    <RuiDivider class="mb-6" />

    <RuiAutoComplete
      v-model="accountingTreatment"
      class="md:w-1/2"
      variant="outlined"
      :options="accountingTreatments"
      key-attr="identifier"
      text-attr="label"
      clearable
      :label="t('accounting_settings.rule.labels.accounting_treatment')"
      :error-messages="toMessages(v$.accountingTreatment)"
      @blur="v$.accountingTreatment.$touch()"
    />
  </form>
</template>
