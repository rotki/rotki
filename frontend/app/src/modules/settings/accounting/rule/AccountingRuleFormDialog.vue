<script lang="ts" setup>
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import { useSaveFailure } from '@/modules/core/form/use-save-failure';
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
const form = useTemplateRef<InstanceType<typeof AccountingRuleForm>>('form');
const stateUpdated = ref<boolean>(false);

const failureTitle = computed<string>(() => editMode
  ? t('accounting_settings.rule.edit_error')
  : t('accounting_settings.rule.add_error'));

const dialogTitle = computed<string>(() => editMode
  ? t('accounting_settings.rule.edit')
  : t('accounting_settings.rule.add'));

const { addAccountingRule, editAccountingRule } = useAccountingApi();
const { capture, clear, failure, modelFieldErrors } = useSaveFailure();

async function persistRule(data: AccountingRuleEntry): Promise<boolean> {
  if (editMode)
    return editAccountingRule(data);

  const ruleData = omit(data, ['identifier']);
  // Include eventIds if provided (for custom accounting rules)
  if (eventIds)
    ruleData.eventIds = eventIds;

  return addAccountingRule(ruleData);
}

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  let success = true;

  set(submitting, true);
  clear();
  try {
    success = await persistRule(data);
  }
  catch (error: unknown) {
    success = false;
    capture(error, data);
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
    :action="{ disabled: loading, primary: t('common.actions.save') }"
    :layout="{ maxWidth: '640px', autoHeight: true }"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    :failure="failure"
    :failure-title="failureTitle"
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
      v-model:error-messages="modelFieldErrors"
      v-model:state-updated="stateUpdated"
      :event-ids="eventIds"
    />
  </BigDialog>
</template>
