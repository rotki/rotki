<script setup lang="ts">
import type { UserNote } from '@/types/notes';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import UserNotesForm from '@/components/notes/UserNotesForm.vue';
import { useUserNotesApi } from '@/composables/api/session/user-notes';
import { logger } from '@/utils/logging';

const open = defineModel<boolean>('open', { required: true });
const model = defineModel<Partial<UserNote>>({ required: true });

const props = defineProps<{
  editMode: boolean;
  location: string;
}>();

const emit = defineEmits<{
  reset: [];
  refresh: [];
}>();

function resetForm() {
  emit('reset');
}

const { t } = useI18n({ useScope: 'global' });

const loading = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const form = useTemplateRef<InstanceType<typeof UserNotesForm>>('form');

const { addUserNote, updateUserNote } = useUserNotesApi();

async function save() {
  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(model);
  let success;
  const editMode = props.editMode;

  set(loading, true);
  try {
    if (editMode)
      success = await updateUserNote(data);
    else
      success = await addUserNote({ ...data, location: props.location });
  }
  catch (error: any) {
    success = false;
    logger.error(error);
  }
  set(loading, false);
  if (success) {
    resetForm();
    emit('refresh');
  }

  return success;
}
</script>

<template>
  <BigDialog
    :display="open"
    :title="editMode ? t('notes_menu.dialog.edit_title') : t('notes_menu.dialog.add_title')"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="resetForm()"
  >
    <UserNotesForm
      ref="form"
      v-model="model"
      v-model:state-updated="stateUpdated"
    />
  </BigDialog>
</template>
