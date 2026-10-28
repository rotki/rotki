<script setup lang="ts">
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { isErr } from 'plainfp/result';
import { useTemplateRef } from 'vue';
import HistoricPriceForm from '@/modules/assets/prices/historic/HistoricPriceForm.vue';
import { useHistoricPrices } from '@/modules/assets/prices/use-historic-price-manager';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const modelValue = defineModel<HistoricalPriceFormPayload | undefined>({ required: true });

const { editMode = false } = defineProps<{
  editMode?: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const loading = ref<boolean>(false);
/** Why the last save failed; the form keeps what was typed, and Save is the retry. */
const saveError = shallowRef<unknown>();
const form = useTemplateRef<InstanceType<typeof HistoricPriceForm>>('form');
const stateUpdated = ref<boolean>(false);

const dialogTitle = computed<string>(() =>
  editMode
    ? t('price_management.dialog.edit_title')
    : t('price_management.dialog.add_title'),
);

const { save: saveAction } = useHistoricPrices();

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = formRef?.validate();
  if (!valid)
    return false;

  set(loading, true);
  set(saveError, undefined);
  const outcome = await saveAction(get(modelValue), editMode);
  set(loading, false);

  if (isErr(outcome)) {
    set(saveError, outcome.error);
    return false;
  }
  if (outcome.value) {
    set(modelValue, undefined);
    emit('refresh');
  }
  return outcome.value;
}

watch(modelValue, (value, previous) => {
  if (!value || !previous)
    set(saveError, undefined);
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :action="{ primary: t('common.actions.save') }"
    :layout="{ autoHeight: true, divide: true, maxWidth: '640px' }"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <FailureStrip
      v-if="saveError"
      :retryable="false"
      class="mb-4"
      :title="editMode ? t('price_management.edit.error.title') : t('price_management.add.error.title')"
      :failure="saveError"
      data-testid="historic-price-save-error"
    />
    <HistoricPriceForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
