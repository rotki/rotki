<script setup lang="ts">
import type { CexMapping } from '@/types/asset';
import ManageCexMappingForm from '@/components/asset-manager/cex-mapping/ManageCexMappingForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { useAssetCexMappingApi } from '@/composables/api/assets/cex-mapping';
import { useMessageStore } from '@/store/message';
import { useTemplateRef } from 'vue';

const modelValue = defineModel<CexMapping | undefined>({ required: true });

const props = withDefaults(defineProps<{
  editMode?: boolean;
}>(), {
  editMode: false,
});

const emit = defineEmits<{
  refresh: [mapping: CexMapping];
}>();

const { t } = useI18n();

const form = useTemplateRef<InstanceType<typeof ManageCexMappingForm>>('form');
const loading = ref(false);
const stateUpdated = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const forAllExchanges = ref<boolean>(false);

const dialogTitle = computed<string>(() =>
  props.editMode
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
  const editMode = props.editMode;
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
