<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { omit } from 'lodash-es';
import AssetIconForm from '@/components/asset-manager/AssetIconForm.vue';
import { toMessages } from '@/utils/validation';
import type { CustomAsset } from '@/types/asset';

const props = withDefaults(
  defineProps<{
    editableItem?: CustomAsset | null;
    types?: string[];
  }>(),
  { editableItem: null, types: () => [] },
);

const { editableItem } = toRefs(props);

const emptyCustomAsset: () => CustomAsset = () => ({
  identifier: '',
  name: '',
  customAssetType: '',
  notes: '',
});

const formData = ref<CustomAsset>(emptyCustomAsset());

function checkEditableItem() {
  const form = get(editableItem);
  if (form)
    set(formData, form);
  else set(formData, emptyCustomAsset());
}

watchImmediate(editableItem, checkEditableItem);

function input(asset: Partial<CustomAsset>) {
  set(formData, { ...get(formData), ...asset });
}

const assetIconFormRef = ref<InstanceType<typeof AssetIconForm> | null>(null);

const { t } = useI18n();

const name = useRefPropVModel(formData, 'name');
const customAssetType = useRefPropVModel(formData, 'customAssetType');

const note = computed<string>({
  get() {
    return get(formData).notes ?? '';
  },
  set(value?: string) {
    input({ notes: value ?? null });
  },
});

const rules = {
  name: {
    required: helpers.withMessage(t('asset_form.name_non_empty'), required),
  },
  type: {
    required: helpers.withMessage(t('asset_form.type_non_empty'), required),
  },
};

const { setValidation, setSubmitFunc } = useCustomAssetForm();

const v$ = setValidation(
  rules,
  {
    name,
    type: customAssetType,
  },
  { $autoDirty: true },
);

function saveIcon(identifier: string) {
  get(assetIconFormRef)?.saveIcon(identifier);
}

const { setMessage } = useMessageStore();
const { editCustomAsset, addCustomAsset } = useAssetManagementApi();

async function save(): Promise<string> {
  const data = get(formData);
  let success = false;
  let identifier = data.identifier;
  const editMode = get(editableItem);

  try {
    if (editMode) {
      success = await editCustomAsset(data);
    }
    else {
      identifier = await addCustomAsset(omit(data, 'identifier'));
      success = !!identifier;
    }

    if (identifier)
      saveIcon(identifier);
  }
  catch (error: any) {
    const obj = { message: error.message };
    setMessage({
      description: editMode ? t('asset_management.edit_error', obj) : t('asset_management.add_error', obj),
    });
  }

  return success ? identifier : '';
}

setSubmitFunc(save);
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <RuiTextField
        v-model="name"
        data-cy="name"
        variant="outlined"
        color="primary"
        clearable
        :label="t('common.name')"
        :error-messages="toMessages(v$.name)"
      />
      <AutoCompleteWithSearchSync
        v-model="customAssetType"
        data-cy="type"
        :items="types"
        clearable
        :label="t('common.type')"
        :error-messages="toMessages(v$.type)"
      />
    </div>
    <RuiTextArea
      v-model="note"
      data-cy="notes"
      variant="outlined"
      color="primary"
      max-rows="5"
      min-rows="3"
      auto-grow
      clearable
      :label="t('common.notes')"
    />

    <AssetIconForm
      ref="assetIconFormRef"
      :identifier="formData.identifier"
    />
  </div>
</template>
