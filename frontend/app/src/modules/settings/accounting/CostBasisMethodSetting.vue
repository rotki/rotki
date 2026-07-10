<script setup lang="ts">
import CostBasisMethodSettings from '@/modules/settings/accounting/CostBasisMethodSettings.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, model, success: writeSuccess } = useSettingModel('costBasisMethod');
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

function getSuccessMessage(method: string): string {
  return t('account_settings.messages.cost_basis_method.success', {
    method: method.toUpperCase(),
  });
}

function getErrorMessage(method: string): string {
  return t('account_settings.messages.cost_basis_method.error', {
    method: method.toUpperCase(),
  });
}

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess(getSuccessMessage(get(model)), true);
});

watch(writeError, (message) => {
  if (message)
    setError(`${getErrorMessage(get(model))}: ${message}`, true);
});
</script>

<template>
  <CostBasisMethodSettings
    v-model="model"
    class="pt-4"
    :success-messages="success ? [success] : []"
    :error-messages="error ? [error] : []"
    :label="t('accounting_settings.trade.labels.cost_basis_method')"
  />
</template>
