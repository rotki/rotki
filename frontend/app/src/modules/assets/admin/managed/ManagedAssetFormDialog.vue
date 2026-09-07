<script setup lang="ts">
import type { SupportedAsset } from '@rotki/common';
import { useTemplateRef } from 'vue';
import ManagedAssetForm from '@/modules/assets/admin/managed/ManagedAssetForm.vue';
import { useManagedAssetFormDialog } from '@/modules/assets/admin/managed/use-managed-asset-form-dialog';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<SupportedAsset | undefined>({ required: true });

const { editMode } = defineProps<{
  editMode: boolean;
  assetTypes: string[];
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const stateUpdated = ref<boolean>(false);
const form = useTemplateRef<InstanceType<typeof ManagedAssetForm>>('form');

const { dialogTitle, loading, modelErrorMessages, save } = useManagedAssetFormDialog({
  editMode: () => editMode,
  form,
  modelValue,
  onSaved: (): void => emit('refresh'),
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :action="{ primary: t('common.actions.save') }"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <ManagedAssetForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="modelErrorMessages"
      v-model:state-updated="stateUpdated"
      :asset-types="assetTypes"
      :loading="loading"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
