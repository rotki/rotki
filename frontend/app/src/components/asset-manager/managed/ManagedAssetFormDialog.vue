<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import ManagedAssetForm from '@/components/asset-manager/managed/ManagedAssetForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useMessageStore } from '@/store/message';
import { ApiValidationError } from '@/types/api/errors';

const modelValue = defineModel<SupportedAsset | undefined>({ required: true });

const props = defineProps<{
  editMode: boolean;
  assetTypes: string[];
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof ManagedAssetForm>>('form');
const stateUpdated = ref(false);

const dialogTitle = computed<string>(() =>
  props.editMode ? t('asset_management.edit_title') : t('asset_management.add_title'),
);

const { setMessage } = useMessageStore();

function getUnderlyingTokenErrors(underlyingTokens: string | Record<string, { address: string[]; weight: string[] }>) {
  if (typeof underlyingTokens === 'string')
    return [underlyingTokens];

  const messages: string[] = [];
  for (const underlyingToken of Object.values(underlyingTokens)) {
    const ut = underlyingToken;
    if (ut.address)
      messages.push(...ut.address);

    if (underlyingTokens.weight)
      messages.push(...ut.weight);
  }
  return messages;
}

interface UnderlyingTokensValidationError {
  underlyingTokens: string | Record<string, { address: string[]; weight: string[] }>;
}

type SchemaValidationError = {
  _schema: string[];
} | {
  Schema: string[];
};

function handleError(
  message:
    | UnderlyingTokensValidationError
    | SchemaValidationError,
) {
  if ('underlyingTokens' in message) {
    const messages = getUnderlyingTokenErrors(message.underlyingTokens);
    setMessage({
      description: messages.join(','),
      title: t('asset_form.underlying_tokens'),
    });
  }
  else {
    const schema = '_schema' in message ? message._schema : message.Schema;
    setMessage({
      description: schema[0],
      title: t('asset_form.underlying_tokens'),
    });
  }
}

const { deleteCacheKey } = useAssetCacheStore();

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  let success;
  let identifier;

  set(loading, true);

  try {
    identifier = await formRef?.saveAsset();
    if (identifier) {
      success = true;

      deleteCacheKey(identifier);

      if (identifier) {
        formRef?.saveIcon(identifier);
      }
    }
    else {
      success = false;
    }
  }
  catch (error: any) {
    success = false;

    let errors = error.message;
    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors({});

    if (typeof errors === 'string') {
      setMessage({
        description: errors,
        title: props.editMode ? t('asset_form.edit_error') : t('asset_form.add_error'),
      });
    }
    else {
      if (errors.underlyingTokens || errors._schema || errors.Schema)
        handleError(errors);

      set(errorMessages, omit(errors, ['underlyingTokens', '_schema', 'Schema']));
      formRef?.validate();
    }
  }

  set(loading, false);
  if (success) {
    set(modelValue, undefined);
    emit('refresh');
  }
  return success;
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
