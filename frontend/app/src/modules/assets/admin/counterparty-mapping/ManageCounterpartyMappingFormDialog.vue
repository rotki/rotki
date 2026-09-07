<script setup lang="ts">
import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import { useTemplateRef } from 'vue';
import ManageCounterpartyMappingForm
  from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingForm.vue';
import { useCounterpartyMappingApi } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-api';
import { useMappingFormDialog } from '@/modules/assets/admin/use-mapping-form-dialog';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<CounterpartyMapping | undefined>({ required: true });

const { editMode } = defineProps<{
  editMode?: boolean;
}>();

const emit = defineEmits<{
  refresh: [mapping: CounterpartyMapping];
}>();

const { t } = useI18n({ useScope: 'global' });

const form = useTemplateRef<InstanceType<typeof ManageCounterpartyMappingForm>>('form');
const stateUpdated = ref<boolean>(false);

const { addCounterpartyMapping, editCounterpartyMapping } = useCounterpartyMappingApi();

const { dialogTitle, loading, modelErrorMessages, save } = useMappingFormDialog({
  add: addCounterpartyMapping,
  edit: editCounterpartyMapping,
  editMode: () => editMode ?? false,
  form,
  modelValue,
  onSaved: (mapping): void => emit('refresh', mapping),
  toPayload: (mapping): CounterpartyMapping => mapping,
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
    <ManageCounterpartyMappingForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="modelErrorMessages"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
