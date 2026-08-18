<script setup lang="ts">
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { toSentenceCase } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { useMappedModelForm } from '@/modules/core/form/use-model-form';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import {
  accountingRuleFormSchema,
  type AccountingRuleFormState,
  accountingRuleFormState,
  applyAccountingRuleFormState,
  TRANSIENT_RULE_KEYS,
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

const form = useMappedModelForm<AccountingRuleEntry, AccountingRuleFormState>({
  model: modelValue,
  schema: accountingRuleFormSchema(),
  serverErrors: errors,
  stateUpdated,
  toModel: (state, rule): AccountingRuleEntry => applyAccountingRuleFormState(rule, state),
  toState: accountingRuleFormState,
  // The three linked toggles are edited here but must not read as unsaved changes.
  transientKeys: TRANSIENT_RULE_KEYS,
});

const accountingTreatments = Object.values(AccountingTreatment).map(identifier => ({
  identifier,
  label: toSentenceCase(identifier),
}));

function touchEventType(): void {
  form.touch('eventType');
  form.touch('eventSubtype');
}

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
    v-model="form.state.taxable"
    class="border-t border-default"
    identifier="taxable"
    :label="t('accounting_settings.rule.labels.taxable')"
    :hint="t('accounting_settings.rule.labels.taxable_subtitle')"
  />

  <AccountingRuleWithLinkedSetting
    v-model="form.state.countEntireAmountSpend"
    class="border-t border-default"
    identifier="countEntireAmountSpend"
    :label="t('accounting_settings.rule.labels.count_entire_amount_spend')"
    :hint="t('accounting_settings.rule.labels.count_entire_amount_spend_subtitle')"
  />

  <AccountingRuleWithLinkedSetting
    v-model="form.state.countCostBasisPnl"
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
