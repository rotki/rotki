<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import omit from 'lodash/omit';
import { type CustomAsset } from '@/types/asset';
import AssetIconForm from '@/components/asset-manager/AssetIconForm.vue';
import { toMessages } from '@/utils/validation';

const props = withDefaults(
  defineProps<{
    edit?: CustomAsset | null;
    types?: string[];
  }>(),
  { edit: null, types: () => [] }
);

const { edit } = toRefs(props);

const emptyCustomAsset: () => CustomAsset = () => ({
  identifier: '',
  name: '',
  customAssetType: '',
  notes: ''
});

const formData = ref<CustomAsset>(emptyCustomAsset());

const checkEditableItem = () => {
  const form = get(edit);
  if (form) {
    set(search, form.customAssetType);
    set(formData, form);
  } else {
    set(search, '');
    set(formData, emptyCustomAsset());
  }
};

watch(edit, checkEditableItem);
onMounted(checkEditableItem);

const input = (asset: Partial<CustomAsset>) => {
  set(formData, { ...get(formData), ...asset });
};

const assetIconFormRef: Ref<InstanceType<typeof AssetIconForm> | null> =
  ref(null);

const { t } = useI18n();

const search = ref<string | null>('');

watch(search, customAssetType => {
  if (customAssetType === null) {
    customAssetType = get(formData).customAssetType;
  }
  input({ customAssetType });
});

const rules = {
  name: {
    required: helpers.withMessage(
      t('asset_form.name_non_empty').toString(),
      required
    )
  },
  type: {
    required: helpers.withMessage(
      t('asset_form.type_non_empty').toString(),
      required
    )
  }
};

const { valid, setValidation, setSubmitFunc } = useCustomAssetForm();

const v$ = setValidation(
  rules,
  {
    name: computed(() => get(formData).name),
    type: computed(() => get(formData).customAssetType)
  },
  { $autoDirty: true }
);

const saveIcon = (identifier: string) => {
  get(assetIconFormRef)?.saveIcon(identifier);
};

const { setMessage } = useMessageStore();
const { editCustomAsset, addCustomAsset } = useAssetManagementApi();

const save = async (): Promise<string> => {
  const data = get(formData);
  let success = false;
  let identifier = data.identifier;
  const editMode = get(edit);

  try {
    if (editMode) {
      success = await editCustomAsset(data);
    } else {
      identifier = await addCustomAsset(omit(data, 'identifier'));
      success = !!identifier;
    }

    if (identifier) {
      saveIcon(identifier);
    }
  } catch (e: any) {
    const obj = { message: e.message };
    setMessage({
      description: editMode
        ? t('asset_management.edit_error', obj)
        : t('asset_management.add_error', obj)
    });
  }

  return success ? identifier : '';
};

setSubmitFunc(save);
</script>

<template>
  <v-form :value="valid">
    <v-row class="mt-2">
      <v-col cols="12" md="6">
        <v-text-field
          data-cy="name"
          :value="formData.name"
          outlined
          persistent-hint
          clearable
          :label="t('common.name')"
          :error-messages="toMessages(v$.name)"
          @input="input({ name: $event })"
        />
      </v-col>
      <v-col cols="12" md="6">
        <v-combobox
          data-cy="type"
          :items="types"
          :value="formData.customAssetType"
          outlined
          persistent-hint
          clearable
          :label="t('common.type')"
          :error-messages="toMessages(v$.type)"
          :search-input.sync="search"
          @input="input({ customAssetType: $event })"
        />
      </v-col>
      <v-col cols="12">
        <v-textarea
          data-cy="notes"
          :value="formData.notes"
          outlined
          persistent-hint
          clearable
          :label="t('asset_form.labels.notes')"
          @input="input({ notes: $event })"
        />
      </v-col>
    </v-row>

    <div class="my-4">
      <asset-icon-form
        ref="assetIconFormRef"
        :identifier="formData.identifier"
      />
    </div>
  </v-form>
</template>
