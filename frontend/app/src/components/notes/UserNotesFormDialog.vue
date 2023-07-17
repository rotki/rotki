<script setup lang="ts">
import { type UserNote } from '@/types/notes';

defineProps<{
  value: Partial<UserNote>;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', newInput: Partial<UserNote>): void;
  (e: 'reset'): void;
}>();

const resetForm = () => {
  emit('reset');
};

const { openDialog, submitting, trySubmit } = useUserNotesForm();

const { t } = useI18n();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="
      editMode
        ? t('notes_menu.dialog.edit_title')
        : t('notes_menu.dialog.add_title')
    "
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <UserNotesForm :value="value" @input="emit('input', $event)" />
  </BigDialog>
</template>
