<script setup lang="ts">
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { useTemplateRef } from 'vue';
import LatestPriceForm from '@/modules/assets/prices/latest/LatestPriceForm.vue';
import { useLatestPrices } from '@/modules/assets/prices/use-latest-price-manager';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const open = defineModel<boolean>('open', { required: true });

const {
  disableFromAsset = false,
  editableItem = null,
  editMode,
} = defineProps<{
  editableItem?: ManualPriceFormPayload | null;
  editMode?: boolean;
  disableFromAsset?: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const modelValue = ref<ManualPriceFormPayload>();
const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof LatestPriceForm>>('form');
const stateUpdated = ref(false);

const emptyPrice: () => ManualPriceFormPayload = () => ({
  fromAsset: '',
  price: '',
  toAsset: '',
});

const { save: saveAction } = useLatestPrices(t);

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  const isEdit = editMode ?? !!editableItem;
  set(loading, true);
  const success = await saveAction(data, isEdit);

  set(loading, false);
  if (success) {
    set(modelValue, undefined);
    emit('refresh');
  }
  return success;
}

const dialogTitle = computed<string>(() =>
  editableItem
    ? t('price_management.dialog.edit_title')
    : t('price_management.dialog.add_title'),
);

watchImmediate([open, () => editableItem], ([open, editableItemVal]) => {
  if (!open) {
    set(modelValue, undefined);
  }
  else {
    if (editableItemVal) {
      set(modelValue, editableItemVal);
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
    :primary-action="t('common.actions.save')"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="open = false"
  >
    <LatestPriceForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode ?? !!editableItem"
      :disable-from-asset="disableFromAsset"
    />
  </BigDialog>
</template>
