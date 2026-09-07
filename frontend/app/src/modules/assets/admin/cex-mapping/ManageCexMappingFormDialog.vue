<script setup lang="ts">
import type { CexMapping } from '@/modules/assets/types';
import { useTemplateRef } from 'vue';
import ManageCexMappingForm from '@/modules/assets/admin/cex-mapping/ManageCexMappingForm.vue';
import { useMappingFormDialog } from '@/modules/assets/admin/use-mapping-form-dialog';
import { useAssetCexMappingApi } from '@/modules/assets/api/use-asset-cex-mapping-api';
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
const stateUpdated = ref<boolean>(false);
const forAllExchanges = ref<boolean>(false);

const { addCexMapping, editCexMapping } = useAssetCexMappingApi();

const { dialogTitle, loading, modelErrorMessages, save } = useMappingFormDialog({
  add: addCexMapping,
  edit: editCexMapping,
  editMode: () => editMode ?? false,
  form,
  modelValue,
  onSaved: (mapping): void => emit('refresh', mapping),
  toPayload: (mapping): CexMapping => ({
    ...mapping,
    location: get(forAllExchanges) ? null : mapping.location,
  }),
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
    <ManageCexMappingForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="modelErrorMessages"
      v-model:state-updated="stateUpdated"
      v-model:for-all-exchanges="forAllExchanges"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
