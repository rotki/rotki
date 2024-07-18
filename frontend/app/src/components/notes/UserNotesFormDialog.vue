<script setup lang="ts">
import type { UserNote } from '@/types/notes';

defineProps<{
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'reset'): void;
}>();

const model = defineModel<Partial<UserNote>>({ required: true });

function resetForm() {
  emit('reset');
}

const { openDialog, submitting, trySubmit } = useUserNotesForm();

const { t } = useI18n();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="editMode ? t('notes_menu.dialog.edit_title') : t('notes_menu.dialog.add_title')"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <UserNotesForm v-model="model" />
  </BigDialog>
</template>
