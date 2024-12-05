<script setup lang="ts">
import { useUserNotesForm } from '@/composables/notes/form';
import type { UserNote } from '@/types/notes';

const model = defineModel<Partial<UserNote>>({ required: true });

defineProps<{
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'reset'): void;
}>();

function resetForm() {
  emit('reset');
}

const { openDialog, stateUpdated, submitting, trySubmit } = useUserNotesForm();

const { t } = useI18n();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="editMode ? t('notes_menu.dialog.edit_title') : t('notes_menu.dialog.add_title')"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <UserNotesForm v-model="model" />
  </BigDialog>
</template>
