<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { CustomAsset } from '@/types/asset';
import AssetIconForm from '@/components/asset-manager/AssetIconForm.vue';
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import { useFormStateWatcher } from '@/composables/form';
import { refOptional, useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const modelValue = defineModel<CustomAsset>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

withDefaults(
  defineProps<{
    editMode?: boolean;
    types?: string[];
  }>(),
  { editMode: false, types: () => [] },
);

const customAssetType = useRefPropVModel(modelValue, 'customAssetType');
const name = useRefPropVModel(modelValue, 'name');
const notes = refOptional(useRefPropVModel(modelValue, 'notes'), '');

const assetIconFormRef = ref<InstanceType<typeof AssetIconForm> | null>(null);

const { t } = useI18n();

const rules = {
  name: {
    required: helpers.withMessage(t('asset_form.name_non_empty'), required),
  },
  notes: { externalServerValidation: () => true },
  type: {
    required: helpers.withMessage(t('asset_form.type_non_empty'), required),
  },
};

const states = {
  name,
  notes,
  type: customAssetType,
};

const v$ = useVuelidate(
  rules,
  states,
  { $autoDirty: true, $externalResults: errors },
);

useFormStateWatcher(states, stateUpdated);

function saveIcon(identifier: string) {
  get(assetIconFormRef)?.saveIcon(identifier);
}

defineExpose({
  saveIcon,
  validate: () => get(v$).$validate(),
});
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
      v-model="notes"
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
      :identifier="modelValue.identifier"
    />
  </div>
</template>
