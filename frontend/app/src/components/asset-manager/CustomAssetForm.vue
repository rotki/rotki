<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import omit from 'lodash/omit';
import { type Ref } from 'vue';
import { type CustomAsset } from '@/types/asset';
import AssetIconForm from '@/components/asset-manager/AssetIconForm.vue';

const props = withDefaults(
  defineProps<{
    edit: boolean;
    types?: string[];
  }>(),
  { types: () => [] }
);

const emptyCustomAsset: () => CustomAsset = () => ({
  identifier: '',
  name: '',
  customAssetType: '',
  notes: ''
});

const formData = ref<CustomAsset>(emptyCustomAsset());

const setForm = (form?: CustomAsset) => {
  if (form) {
    set(search, form.customAssetType);
    set(formData, form);
  } else {
    set(search, '');
    set(formData, emptyCustomAsset());
  }
};

const emit = defineEmits<{
  (e: 'valid', valid: boolean): void;
}>();

const { edit } = toRefs(props);

const input = (asset: Partial<CustomAsset>) => {
  set(formData, { ...get(formData), ...asset });
};

const assetIconFormRef: Ref<InstanceType<typeof AssetIconForm> | null> =
  ref(null);

const { t, tc } = useI18n();

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

const v$ = useVuelidate(
  rules,
  {
    name: computed(() => get(formData).name),
    type: computed(() => get(formData).customAssetType)
  },
  { $autoDirty: true }
);

watch(v$, ({ $invalid }) => {
  emit('valid', !$invalid);
});

const saveIcon = (identifier: string) => {
  get(assetIconFormRef)?.saveIcon(identifier);
};

const { setMessage } = useMessageStore();
const { editCustomAsset, addCustomAsset } = useAssetManagementApi();

const save = async () => {
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
        ? tc('asset_management.edit_error', 0, obj)
        : tc('asset_management.add_error', 0, obj)
    });
  }

  return success ? identifier : '';
};

defineExpose({
  saveIcon,
  setForm,
  save
});
</script>
<template>
  <v-form :value="!v$.$invalid">
    <v-row class="mt-2">
      <v-col cols="12" md="6">
        <v-text-field
          data-cy="name"
          :value="formData.name"
          outlined
          persistent-hint
          clearable
          :label="t('common.name')"
          :error-messages="v$.name.$errors.map(e => e.$message)"
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
          :error-messages="v$.type.$errors.map(e => e.$message)"
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
