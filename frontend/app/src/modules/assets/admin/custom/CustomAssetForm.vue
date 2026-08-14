<script setup lang="ts">
import type { ZodType } from 'zod';
import type { CustomAsset } from '@/modules/assets/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import AssetIconForm from '@/modules/assets/admin/AssetIconForm.vue';
import { customAssetSchema } from '@/modules/assets/admin/custom/custom-asset-form';
import { useModelForm } from '@/modules/core/form/use-model-form';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';

const modelValue = defineModel<CustomAsset>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { types } = defineProps<{
  types: string[];
}>();

const assetIconFormRef = useTemplateRef<InstanceType<typeof AssetIconForm>>('assetIconFormRef');

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => customAssetSchema({
  customAssetType: t('asset_form.type_non_empty'),
  name: t('asset_form.name_non_empty'),
}));

const form = useModelForm<CustomAsset>({
  model: modelValue,
  schema,
  serverErrors: errors,
  stateUpdated,
});

/** The field shows an empty box for an asset with no notes, and clearing it puts one back. */
const notes = computed<string>({
  get: () => form.state.notes ?? '',
  set: (value?: string) => {
    form.state.notes = value ?? null;
  },
});

function saveIcon(identifier: string): void {
  get(assetIconFormRef)?.saveIcon(identifier);
}

defineExpose({
  saveIcon,
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <RuiTextField
        v-model="form.state.name"
        data-testid="name"
        variant="outlined"
        color="primary"
        clearable
        :label="t('common.name')"
        :error-messages="form.errors('name')"
        @update:model-value="form.touch('name')"
      />
      <AutoCompleteWithSearchSync
        v-model="form.state.customAssetType"
        data-testid="type"
        :items="types"
        clearable
        :label="t('common.type')"
        :error-messages="form.errors('customAssetType')"
        @update:model-value="form.touch('customAssetType')"
      />
    </div>
    <RuiTextArea
      v-model="notes"
      data-testid="notes"
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
