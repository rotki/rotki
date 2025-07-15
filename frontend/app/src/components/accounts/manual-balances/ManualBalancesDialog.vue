<script setup lang="ts">
import type { ManualBalance, RawManualBalance } from '@/types/manual-balances';
import { startPromise } from '@shared/utils';
import { useTemplateRef } from 'vue';
import ManualBalancesForm from '@/components/accounts/manual-balances/ManualBalancesForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { useBalances } from '@/composables/balances';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useMessageStore } from '@/store/message';

const modelValue = defineModel<ManualBalance | RawManualBalance | undefined>({ required: true });

const emit = defineEmits<{
  (e: 'update-tab', tab: string | number): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof ManualBalancesForm>>('form');
const stateUpdated = ref(false);

const { setMessage } = useMessageStore();
const { save: saveBalance } = useManualBalances();

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

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  set(loading, true);

  await get(form)?.savePrice();

  const payload = get(modelValue);
  const status = await saveBalance(payload);

  startPromise(refreshPrices(true));

  if (status.success) {
    set(modelValue, undefined);
    set(loading, false);

    if (!('identifier' in payload)) {
      emit('update-tab', payload.balanceType === 'asset' ? 'assets' : 'liabilities');
    }

    return true;
  }

  if (status.message) {
    if (typeof status.message !== 'string') {
      set(errorMessages, status.message);
      await formRef?.validate();
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
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <ManualBalancesForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :submitting="loading"
    />
  </BigDialog>
</template>
