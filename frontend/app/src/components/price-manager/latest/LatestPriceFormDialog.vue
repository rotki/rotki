<script setup lang="ts">
import type { ManualPriceFormPayload } from '@/types/prices';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import LatestPriceForm from '@/components/price-manager/latest/LatestPriceForm.vue';
import { useLatestPrices } from '@/composables/price-manager/latest';

const open = defineModel<boolean>('open', { required: true });

const props = withDefaults(
  defineProps<{
    editableItem?: ManualPriceFormPayload | null;
    editMode?: boolean;
    disableFromAsset?: boolean;
  }>(),
  {
    disableFromAsset: false,
    editableItem: null,
    editMode: undefined,
  },
);

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const { editableItem, editMode } = toRefs(props);

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
  const isEdit = get(editMode) ?? !!get(editableItem);
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
  get(editableItem)
    ? t('price_management.dialog.edit_title')
    : t('price_management.dialog.add_title'),
);

watchImmediate([open, editableItem], ([open, editableItem]) => {
  if (!open) {
    set(modelValue, undefined);
  }
  else {
    if (editableItem) {
      set(modelValue, editableItem);
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
