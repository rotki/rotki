<script setup lang="ts">
import type { CustomAsset } from '@/modules/assets/types';
import { useTemplateRef } from 'vue';
import CustomAssetForm from '@/modules/assets/admin/custom/CustomAssetForm.vue';
import { useCustomAssetFormDialog } from '@/modules/assets/admin/custom/use-custom-asset-form-dialog';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const open = defineModel<boolean>('open', { required: true });
const savedAssetId = defineModel<string>('savedAssetId', { required: false });

const {
  editableItem = null,
  types = [],
} = defineProps<{
  editableItem?: CustomAsset | null;
  types?: string[];
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const form = useTemplateRef<InstanceType<typeof CustomAssetForm>>('form');
const stateUpdated = ref<boolean>(false);

const { dialogTitle, loading, modelErrorMessages, modelValue, save } = useCustomAssetFormDialog({
  editableItem: () => editableItem,
  form,
  onSaved: (identifier): void => {
    emit('refresh');
    set(savedAssetId, identifier);
  },
  open,
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
    @cancel="open = false"
  >
    <CustomAssetForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="modelErrorMessages"
      v-model:state-updated="stateUpdated"
      :types="types"
    />
  </BigDialog>
</template>
