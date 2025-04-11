<script setup lang="ts">
import type { CounterpartyMapping } from '@/modules/asset-manager/counterparty-mapping/schema';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ManageCounterpartyMappingForm from '@/modules/asset-manager/counterparty-mapping/ManageCounterpartyMappingForm.vue';
import { useCounterpartyMappingApi } from '@/modules/asset-manager/counterparty-mapping/use-counterparty-mapping-api';
import { useMessageStore } from '@/store/message';
import { useTemplateRef } from 'vue';

const modelValue = defineModel<CounterpartyMapping | undefined>({ required: true });

const props = withDefaults(defineProps<{
  editMode?: boolean;
}>(), {
  editMode: false,
});

const emit = defineEmits<{
  refresh: [mapping: CounterpartyMapping];
}>();

const { t } = useI18n();

const form = useTemplateRef<InstanceType<typeof ManageCounterpartyMappingForm>>('form');
const loading = ref(false);
const stateUpdated = ref(false);
const errorMessages = ref<Record<string, string[]>>({});

const dialogTitle = computed<string>(() =>
  props.editMode
    ? t('asset_management.cex_mapping.edit_title')
    : t('asset_management.cex_mapping.add_title'),
);

const { addCounterpartyMapping, editCounterpartyMapping } = useCounterpartyMappingApi();
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
  const editMode = props.editMode;

  set(loading, true);
  try {
    if (editMode)
      success = await editCounterpartyMapping(data);
    else
      success = await addCounterpartyMapping(data);
  }
  catch (error: any) {
    success = false;
    const obj = { message: error.message };
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
    <ManageCounterpartyMappingForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :edit-mode="editMode"
    />
  </BigDialog>
</template>
