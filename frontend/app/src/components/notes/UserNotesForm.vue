<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import type { UserNote } from '@/types/notes';

const props = defineProps<{
  modelValue: Partial<UserNote>;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', newInput: Partial<UserNote>): void;
}>();

const { t } = useI18n();

const title = useSimplePropVModel(props, 'title', emit);
const content = useSimplePropVModel(props, 'content', emit);

const { setValidation } = useUserNotesForm();

const rules = {
  content: {
    required: helpers.withMessage(t('notes_menu.rules.content.non_empty').toString(), required),
  },
};

const v$ = setValidation(rules, { content }, { $autoDirty: true });
</script>

<template>
  <div>
    <RuiTextField
      v-model="title"
      variant="outlined"
      color="primary"
      :label="t('notes_menu.labels.title')"
    />
    <RuiTextArea
      v-model="content"
      variant="outlined"
      color="primary"
      min-rows="3"
      rows="10"
      auto-grow
      :label="t('notes_menu.labels.content')"
      :error-messages="toMessages(v$.content)"
    />
  </div>
</template>
