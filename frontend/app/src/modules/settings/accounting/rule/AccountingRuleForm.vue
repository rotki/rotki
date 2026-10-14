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

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <section class="flex flex-col gap-3">
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
        :label="t('common.counterparty')"
        :disabled="isEventSpecificRule"
        :error-messages="form.errors('counterparty')"
        @blur="form.touch('counterparty')"
      />
    </section>

    <section class="flex flex-col gap-2">
      <span class="text-sm font-medium text-rui-text">
        {{ t('accounting_settings.rule.sections.accounting') }}
      </span>
      <div class="rounded-rui-control border border-rui-divider between:border-t between:border-rui-divider">
        <AccountingRuleWithLinkedSetting
          v-model="form.state.taxable"
          identifier="taxable"
          :label="t('accounting_settings.rule.labels.taxable')"
          :hint="t('accounting_settings.rule.labels.taxable_subtitle')"
        />
        <AccountingRuleWithLinkedSetting
          v-model="form.state.countEntireAmountSpend"
          identifier="countEntireAmountSpend"
          :label="t('accounting_settings.rule.labels.count_entire_amount_spend')"
          :hint="t('accounting_settings.rule.labels.count_entire_amount_spend_subtitle')"
        />
        <AccountingRuleWithLinkedSetting
          v-model="form.state.countCostBasisPnl"
          identifier="countCostBasisPnl"
          :label="t('accounting_settings.rule.labels.count_cost_basis_pnl')"
          :hint="t('accounting_settings.rule.labels.count_cost_basis_pnl_subtitle')"
          :learn-more-url="externalLinks.usageGuideSection.accountingRuleCountCostBasisPnl"
        />
      </div>
      <div>
        <RuiAutoComplete
          v-model="form.state.accountingTreatment"
          :options="accountingTreatments"
          key-attr="identifier"
          text-attr="label"
          clearable
          :label="t('accounting_settings.rule.labels.accounting_treatment')"
          :hint="t('accounting_settings.rule.labels.accounting_treatment_subtitle')"
          :error-messages="form.errors('accountingTreatment')"
          @blur="form.touch('accountingTreatment')"
        />
        <div class="flex flex-wrap items-center gap-x-3 text-xs text-rui-text-secondary">
          {{ t('accounting_settings.rule.learn_more') }}:
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
      </div>
    </section>
  </div>
</template>
