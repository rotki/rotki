<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import ManagedAssetForm from '@/components/asset-manager/managed/ManagedAssetForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { ApiValidationError, type ValidationErrors } from '@/modules/api/types/errors';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { useMessageStore } from '@/store/message';

const modelValue = defineModel<SupportedAsset | undefined>({ required: true });

const { editMode } = defineProps<{
  editMode: boolean;
  assetTypes: string[];
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const loading = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof ManagedAssetForm>>('form');

const dialogTitle = computed<string>(() =>
  editMode ? t('asset_management.edit_title') : t('asset_management.add_title'),
);

const { setMessage } = useMessageStore();
const { deleteCacheKey } = useAssetInfoCache();

function handleValidationErrors(errors: ValidationErrors): void {
  if ('underlyingTokens' in errors) {
    const underlyingTokens = errors.underlyingTokens;
    if (underlyingTokens) {
      const messages = Array.isArray(underlyingTokens) ? underlyingTokens : [underlyingTokens];
      setMessage({
        description: messages.join(','),
        title: t('asset_form.underlying_tokens'),
      });
    }
  }
  else {
    const schema = '_schema' in errors ? errors._schema : errors.Schema;
    if (Array.isArray(schema)) {
      setMessage({
        description: schema[0],
        title: t('asset_form.underlying_tokens'),
      });
    }
  }
}

function handleSaveError(error: unknown): void {
  let errors: string | ValidationErrors = getErrorMessage(error);
  if (error instanceof ApiValidationError)
    errors = error.getValidationErrors({});

  if (typeof errors === 'string') {
    setMessage({
      description: errors,
      title: editMode ? t('asset_form.edit_error') : t('asset_form.add_error'),
    });
    return;
  }

  if ('underlyingTokens' in errors || '_schema' in errors || 'Schema' in errors)
    handleValidationErrors(errors);

  set(errorMessages, omit(errors, ['underlyingTokens', '_schema', 'Schema']));
  get(form)?.validate();
}

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  set(loading, true);
  try {
    const identifier = await formRef?.saveAsset();
    if (!identifier) {
      return false;
    }

    deleteCacheKey(identifier);
    formRef?.saveIcon(identifier);
    set(modelValue, undefined);
    emit('refresh');
    return true;
  }
  catch (error: unknown) {
    handleSaveError(error);
    return false;
  }
  finally {
    set(loading, false);
  }
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :primary-action="t('common.actions.save')"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <ManagedAssetForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :asset-types="assetTypes"
      :loading="loading"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
