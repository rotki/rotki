<script setup lang="ts">
import type { CustomAsset } from '@/types/asset';
import CustomAssetForm from '@/components/asset-manager/custom/CustomAssetForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { useAssetManagementApi } from '@/composables/api/assets/management';
import { useMessageStore } from '@/store/message';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';

const open = defineModel<boolean>('open', { required: true });
const savedAssetId = defineModel<string>('savedAssetId', { required: false });

const props = withDefaults(
  defineProps<{
    editableItem?: CustomAsset | null;
    types?: string[];
  }>(),
  {
    editableItem: null,
    types: () => [],
  },
);

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const { editableItem } = toRefs(props);
const { t } = useI18n({ useScope: 'global' });

const modelValue = ref<CustomAsset>();
const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof CustomAssetForm>>('form');
const stateUpdated = ref(false);

const { setMessage } = useMessageStore();
const { addCustomAsset, editCustomAsset } = useAssetManagementApi();

const emptyCustomAsset: () => CustomAsset = () => ({
  customAssetType: '',
  identifier: '',
  name: '',
  notes: '',
});

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  let success;
  let identifier = data.identifier;

  const editMode = !!get(editableItem);
  set(loading, true);
  try {
    if (editMode) {
      success = await editCustomAsset(data);
    }
    else {
      identifier = await addCustomAsset(omit(data, ['identifier']));
      success = !!identifier;
    }

    if (identifier) {
      formRef?.saveIcon(identifier);
    }
  }
  catch (error: any) {
    success = false;
    const obj = { message: error.message };
    setMessage({
      description: editMode
        ? t('asset_management.edit_error', obj)
        : t('asset_management.add_error', obj),
    });
  }

  set(loading, false);
  if (success) {
    set(modelValue, undefined);
    emit('refresh');
    set(savedAssetId, identifier);
  }
  return success;
}

const dialogTitle = computed<string>(() =>
  get(editableItem)
    ? t('asset_management.edit_title')
    : t('asset_management.add_title'),
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
      set(modelValue, emptyCustomAsset());
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
    <CustomAssetForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :types="types"
      :edit-mode="!!editableItem"
    />
  </BigDialog>
</template>
