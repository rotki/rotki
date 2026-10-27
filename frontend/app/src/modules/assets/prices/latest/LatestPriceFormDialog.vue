<script setup lang="ts">
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { isErr } from 'plainfp/result';
import { useTemplateRef } from 'vue';
import LatestPriceForm from '@/modules/assets/prices/latest/LatestPriceForm.vue';
import { useLatestPrices } from '@/modules/assets/prices/use-latest-price-manager';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const open = defineModel<boolean>('open', { required: true });

const {
  disableFromAsset = false,
  editableItem = null,
  editMode,
  prefill = null,
} = defineProps<{
  editableItem?: ManualPriceFormPayload | null;
  editMode?: boolean;
  disableFromAsset?: boolean;
  prefill?: ManualPriceFormPayload | null;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const failureMessage = useFailureMessage();

const modelValue = ref<ManualPriceFormPayload>();
const loading = ref(false);
/** Why the last save failed; the form keeps what was typed, and Save is the retry. */
const saveError = shallowRef<unknown>();
const form = useTemplateRef<InstanceType<typeof LatestPriceForm>>('form');
const stateUpdated = ref(false);

const emptyPrice: () => ManualPriceFormPayload = () => ({
  fromAsset: '',
  price: '',
  toAsset: '',
});

const { save: saveAction } = useLatestPrices();

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = formRef?.validate();
  if (!valid)
    return false;

  set(loading, true);
  set(saveError, undefined);
  const outcome = await saveAction(get(modelValue));
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

const saveErrorTitle = computed<string>(() =>
  (editMode ?? !!editableItem)
    ? t('price_management.edit.error.title')
    : t('price_management.add.error.title'),
);

const dialogTitle = computed<string>(() =>
  editableItem
    ? t('price_management.dialog.edit_title')
    : t('price_management.dialog.add_title'),
);

watchImmediate([open, () => editableItem, () => prefill], ([open, editableItemVal, prefillVal]) => {
  set(saveError, undefined);
  if (!open) {
    set(modelValue, undefined);
  }
  else {
    if (editableItemVal) {
      set(modelValue, editableItemVal);
    }
    else if (prefillVal) {
      set(modelValue, { ...prefillVal });
    }
    else {
      set(modelValue, emptyPrice());
    }
  }
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
    @cancel="open = false"
  >
    <FailureStrip
      v-if="saveError"
      :retryable="false"
      class="mb-4"
      :title="saveErrorTitle"
      :message="failureMessage(saveError)"
      data-testid="latest-price-save-error"
    />
    <LatestPriceForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode ?? !!editableItem"
      :disable-from-asset="disableFromAsset"
    />
  </BigDialog>
</template>
