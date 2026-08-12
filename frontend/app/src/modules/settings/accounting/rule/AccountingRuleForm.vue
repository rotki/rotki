<script setup lang="ts">
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { toSentenceCase } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { useForm } from '@/modules/core/form/use-form';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import {
  accountingRuleFormSchema,
  type AccountingRuleFormState,
  accountingRuleFormState,
  applyAccountingRuleFormState,
} from '@/modules/settings/accounting/rule/accounting-rule-form';
import AccountingRuleWithLinkedSetting from '@/modules/settings/accounting/rule/AccountingRuleWithLinkedSetting.vue';
import { type AccountingRuleEntry, AccountingTreatment } from '@/modules/settings/types/accounting';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const modelValue = defineModel<AccountingRuleEntry>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { eventIds } = defineProps<{
  eventIds?: number[];
}>();

const { t } = useI18n({ useScope: 'global' });

const isEventSpecificRule = computed<boolean>(() => !!eventIds && eventIds.length > 0);

// The three linked toggles carry no validation and do not mark the form dirty, so they stay bound
// straight to the model rather than joining the form state.
const taxable = useRefPropVModel(modelValue, 'taxable');
const countEntireAmountSpend = useRefPropVModel(modelValue, 'countEntireAmountSpend');
const countCostBasisPnl = useRefPropVModel(modelValue, 'countCostBasisPnl');

const form = useForm<AccountingRuleFormState, AccountingRuleFormState>({
  initial: (): AccountingRuleFormState => accountingRuleFormState(get(modelValue)),
  schema: accountingRuleFormSchema(),
  // The dialog owns the persist and reads the model, so there is nothing to submit from here.
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): AccountingRuleFormState => ({ ...state }),
});

const accountingTreatments = Object.values(AccountingTreatment).map(identifier => ({
  identifier,
  label: toSentenceCase(identifier),
}));

function touchEventType(): void {
  form.touch('eventType');
  form.touch('eventSubtype');
}

// Non-immediate on purpose: seeding must not write the mapped blank counterparty over a rule that
// legitimately has none.
watch(() => ({ ...form.state }), (state) => {
  set(modelValue, applyAccountingRuleFormState(get(modelValue), state));
});

watch(errors, (value) => {
  form.setServerErrors(toServerErrors(value));
}, { deep: true, immediate: true });

watch(form.dirty, (dirty) => {
  set(stateUpdated, dirty);
});

// The dialog keeps its prompt-on-close flag across opens, so hand it back disarmed.
onUnmounted(() => {
  set(stateUpdated, false);
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <HistoryEventTypeForm
    v-model:event-type="form.state.eventType"
    v-model:event-subtype="form.state.eventSubtype"
    :counterparty="form.state.counterparty"
    :error-messages="{
      eventType: form.errors('eventType'),
      eventSubtype: form.errors('eventSubtype'),
    }"
    :disabled="isEventSpecificRule"
    disable-warning
    @touch="touchEventType()"
  />

  <CounterpartyInput
    v-model="form.state.counterparty"
    class="md:w-1/2"
    :label="t('common.counterparty')"
    :disabled="isEventSpecificRule"
    :error-messages="form.errors('counterparty')"
    @blur="form.touch('counterparty')"
  />

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
    :learn-more-url="externalLinks.usageGuideSection.accountingRuleCountCostBasisPnl"
  />

  <RuiDivider class="mb-6" />

  <RuiAutoComplete
    v-model="form.state.accountingTreatment"
    class="md:w-1/2"
    variant="outlined"
    :options="accountingTreatments"
    key-attr="identifier"
    text-attr="label"
    clearable
    :label="t('accounting_settings.rule.labels.accounting_treatment')"
    :hint="t('accounting_settings.rule.labels.accounting_treatment_subtitle')"
    :error-messages="form.errors('accountingTreatment')"
    @blur="form.touch('accountingTreatment')"
  />
  <div class="text-rui-text-secondary text-caption flex items-center gap-3 md:w-1/2 mt-1">
    <span class="inline-flex items-center gap-1">
      <RuiIcon
        name="lu-book-open"
        size="14"
      />
      {{ t('accounting_settings.rule.learn_more') }}:
    </span>
    <ExternalLink
      :url="externalLinks.usageGuideSection.accountingTreatmentSwap"
      color="primary"
      :text="t('accounting_settings.rule.labels.accounting_treatment_swap')"
    />
    <ExternalLink
      :url="externalLinks.usageGuideSection.accountingTreatmentBasisTransfer"
      color="primary"
      :text="t('accounting_settings.rule.labels.accounting_treatment_basis_transfer')"
    />
  </div>
</template>
