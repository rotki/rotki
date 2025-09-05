<script lang="ts" setup>
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import AccountingRuleForm from '@/components/settings/accounting/rule/AccountingRuleForm.vue';
import { useAccountingApi } from '@/composables/api/settings/accounting-api';
import { useMessageStore } from '@/store/message';
import { ApiValidationError } from '@/types/api/errors';

const modelValue = defineModel<AccountingRuleEntry | undefined>({ required: true });

const props = withDefaults(
  defineProps<{
    editMode?: boolean;
    loading?: boolean;
    eventIds?: number[];
  }>(),
  {
    editMode: false,
    eventIds: undefined,
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const submitting = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof AccountingRuleForm>>('form');
const stateUpdated = ref(false);

const dialogTitle = computed<string>(() => props.editMode
  ? t('accounting_settings.rule.edit')
  : t('accounting_settings.rule.add'));

const { addAccountingRule, editAccountingRule } = useAccountingApi();
const { setMessage } = useMessageStore();

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  let success;
  const editMode = props.editMode;
  set(submitting, true);
  try {
    if (editMode) {
      success = await editAccountingRule(data);
    }
    else {
      const ruleData = omit(data, ['identifier']);
      // Include eventIds if provided (for custom accounting rules)
      if (props.eventIds)
        ruleData.eventIds = props.eventIds;
      success = await addAccountingRule(ruleData);
    }
  }
  catch (error: any) {
    success = false;
    const errorTitle = editMode
      ? t('accounting_settings.rule.edit_error')
      : t('accounting_settings.rule.add_error');

    let errors = error.message;
    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(data);

    if (typeof errors === 'string') {
      setMessage({
        description: errors,
        success: false,
        title: errorTitle,
      });
    }
    else {
      set(errorMessages, errors);
    }
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
    <AccountingRuleForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
    />
  </BigDialog>
</template>
