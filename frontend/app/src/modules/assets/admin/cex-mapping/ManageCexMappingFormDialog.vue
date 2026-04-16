<script setup lang="ts">
import type { CexMapping } from '@/modules/assets/types';
import { useTemplateRef } from 'vue';
import ManageCexMappingForm from '@/modules/assets/admin/cex-mapping/ManageCexMappingForm.vue';
import { useAssetCexMappingApi } from '@/modules/assets/api/use-asset-cex-mapping-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<CexMapping | undefined>({ required: true });

const { editMode } = defineProps<{
  editMode?: boolean;
}>();

const emit = defineEmits<{
  refresh: [mapping: CexMapping];
}>();

const { t } = useI18n({ useScope: 'global' });

const form = useTemplateRef<InstanceType<typeof ManageCexMappingForm>>('form');
const loading = ref(false);
const stateUpdated = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const forAllExchanges = ref<boolean>(false);

const dialogTitle = computed<string>(() =>
  editMode
    ? t('asset_management.cex_mapping.edit_title')
    : t('asset_management.cex_mapping.add_title'),
);

const { addCexMapping, editCexMapping } = useAssetCexMappingApi();
const { setMessage } = useMessageStore();

async function save(): Promise<boolean> {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  let success;
  const payload = {
    ...data,
    location: get(forAllExchanges) ? null : data.location,
  };

  set(loading, true);
  try {
    if (editMode)
      success = await editCexMapping(payload);
    else
      success = await addCexMapping(payload);
  }
  catch (error: unknown) {
    success = false;
    const obj = { message: getErrorMessage(error) };
    setMessage({
      description: editMode
        ? t('asset_management.cex_mapping.add_error', obj)
        : t('asset_management.cex_mapping.edit_error', obj),
    });
  }

  set(loading, false);
  if (success) {
    const mapping = get(modelValue);
    set(modelValue, undefined);
    emit('refresh', mapping);
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
    <ManageCexMappingForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      v-model:for-all-exchanges="forAllExchanges"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
