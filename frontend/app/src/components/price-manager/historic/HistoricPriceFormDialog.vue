<script setup lang="ts">
import type { HistoricalPriceFormPayload } from '@/modules/prices/price-types';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import HistoricPriceForm from '@/components/price-manager/historic/HistoricPriceForm.vue';
import { useHistoricPrices } from '@/composables/price-manager/historic';

const modelValue = defineModel<HistoricalPriceFormPayload | undefined>({ required: true });

const { editMode = false } = defineProps<{
  editMode?: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const loading = ref<boolean>(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof HistoricPriceForm>>('form');
const stateUpdated = ref<boolean>(false);

const dialogTitle = computed<string>(() =>
  editMode
    ? t('price_management.dialog.edit_title')
    : t('price_management.dialog.add_title'),
);

const { save: saveAction } = useHistoricPrices(t);

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  set(loading, true);
  const success = await saveAction(data, editMode);

  set(loading, false);
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
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <HistoricPriceForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
