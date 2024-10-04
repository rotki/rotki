<script setup lang="ts">
import { useTemplateRef } from 'vue';
import ManualBalancesForm from '@/components/accounts/manual-balances/ManualBalancesForm.vue';
import type { ManualBalance, RawManualBalance } from '@/types/manual-balances';

const modelValue = defineModel<ManualBalance | RawManualBalance | undefined>({ required: true });

const { t } = useI18n();

const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof ManualBalancesForm>>('form');

const { setMessage } = useMessageStore();
const { save: saveBalance } = useManualBalancesStore();

const { refreshPrices } = useBalances();

const isEdit = computed<boolean>(() => isDefined(modelValue) && 'identifier' in get(modelValue));

const dialogTitle = computed<string>(() => {
  if (get(isEdit))
    return t('manual_balances.dialog.edit.title');
  return t('manual_balances.dialog.add.title');
});

const dialogSubtitle = computed<string>(() => {
  if (get(isEdit))
    return t('manual_balances.dialog.edit.subtitle');
  return '';
});

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  set(loading, true);

  await get(form)?.savePrice();

  const status = await saveBalance(get(modelValue));

  startPromise(refreshPrices(true));

  if (status.success) {
    set(modelValue, undefined);
    set(loading, false);
    return true;
  }

  if (status.message) {
    if (typeof status.message !== 'string') {
      set(errorMessages, status.message);
      await get(form)?.validate();
    }
    else {
      const obj = { message: status.message };
      setMessage({
        description: get(isEdit)
          ? t('actions.manual_balances.edit.error.description', obj)
          : t('actions.manual_balances.add.error.description', obj),
      });
    }
  }
  set(loading, false);
  return false;
}
</script>

<template>
  <BigDialog
    v-if="modelValue"
    :display="!!modelValue"
    :title="dialogTitle"
    :subtitle="dialogSubtitle"
    :loading="loading"
    :primary-action="t('common.actions.save')"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <ManualBalancesForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      :submitting="loading"
    />
  </BigDialog>
</template>
