<script lang="ts" setup>
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import AccountingRuleForm from '@/modules/settings/accounting/rule/AccountingRuleForm.vue';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<AccountingRuleEntry | undefined>({ required: true });

const { editMode = false, loading = false, eventIds } = defineProps<{
  editMode?: boolean;
  loading?: boolean;
  eventIds?: number[];
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const submitting = ref<boolean>(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof AccountingRuleForm>>('form');
const stateUpdated = ref<boolean>(false);

const dialogTitle = computed<string>(() => editMode
  ? t('accounting_settings.rule.edit')
  : t('accounting_settings.rule.add'));

const { addAccountingRule, editAccountingRule } = useAccountingApi();
const { setMessage } = useMessageStore();

async function persistRule(data: AccountingRuleEntry): Promise<boolean> {
  if (editMode)
    return editAccountingRule(data);

  const ruleData = omit(data, ['identifier']);
  // Include eventIds if provided (for custom accounting rules)
  if (eventIds)
    ruleData.eventIds = eventIds;

  return addAccountingRule(ruleData);
}

/**
 * Field-level errors go back to the form so it can mark the offending inputs; anything else has no
 * field to attach to and is surfaced as a message.
 */
function reportSaveFailure(error: unknown, data: AccountingRuleEntry): void {
  const errors: string | ValidationErrors = error instanceof ApiValidationError
    ? error.getValidationErrors(data)
    : getErrorMessage(error);

  if (typeof errors !== 'string') {
    set(errorMessages, errors);
    return;
  }

  setMessage({
    description: errors,
    success: false,
    title: editMode
      ? t('accounting_settings.rule.edit_error')
      : t('accounting_settings.rule.add_error'),
  });
}

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  let success = true;

  set(submitting, true);
  try {
    success = await persistRule(data);
  }
  catch (error: unknown) {
    success = false;
    reportSaveFailure(error, data);
  }
  set(submitting, false);

  if (success) {
    set(modelValue, undefined);
    emit('refresh');
  }

  return success;
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <template
      v-if="eventIds && eventIds.length > 0"
      #subtitle
    >
      {{ t('accounting_settings.rule.custom_events_info', { count: eventIds.length }) }}
    </template>
    <AccountingRuleForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :event-ids="eventIds"
    />
  </BigDialog>
</template>
