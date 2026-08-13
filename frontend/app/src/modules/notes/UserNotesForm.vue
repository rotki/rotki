<script setup lang="ts">
import type { ZodType } from 'zod';
import type { UserNoteDraft } from '@/modules/core/common/notes';
import { useModelForm } from '@/modules/core/form/use-model-form';
import { userNoteSchema } from '@/modules/notes/note-forms';

const modelValue = defineModel<UserNoteDraft>({ required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => userNoteSchema({
  content: t('notes_menu.rules.content.non_empty'),
}));

const form = useModelForm<UserNoteDraft>({
  model: modelValue,
  schema,
  stateUpdated,
  // The note carries these through the form; only the two fields it renders count as an edit.
  transientKeys: ['identifier', 'isPinned', 'lastUpdateTimestamp', 'location'],
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div>
    <RuiTextField
      v-model="form.state.title"
      variant="outlined"
      color="primary"
      :label="t('notes_menu.labels.title')"
    />
    <RuiTextArea
      v-model="form.state.content"
      variant="outlined"
      color="primary"
      min-rows="3"
      rows="10"
      auto-grow
      :label="t('notes_menu.labels.content')"
      :error-messages="form.errors('content')"
      @update:model-value="form.touch('content')"
    />
  </div>
</template>
