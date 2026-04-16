<script setup lang="ts">
import type { UserNote } from '@/modules/core/common/notes';
import { useTemplateRef } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';
import { useUserNotesApi } from '@/modules/notes/use-user-notes-api';
import UserNotesForm from '@/modules/notes/UserNotesForm.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const open = defineModel<boolean>('open', { required: true });
const model = defineModel<Partial<UserNote>>({ required: true });

const { editMode, location } = defineProps<{
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
  set(loading, true);
  try {
    if (editMode)
      success = await updateUserNote(data);
    else
      success = await addUserNote({ ...data, location });
  }
  catch (error: unknown) {
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
