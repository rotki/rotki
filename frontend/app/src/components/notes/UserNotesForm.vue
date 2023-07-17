<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { type UserNote } from '@/types/notes';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  value: Partial<UserNote>;
}>();

const emit = defineEmits<{
  (e: 'input', newInput: Partial<UserNote>): void;
}>();

const { t } = useI18n();
const { value } = toRefs(props);

const input = (newInput: Partial<UserNote>) => {
  emit('input', { ...get(value), ...newInput });
};

const { valid, setValidation } = useUserNotesForm();

const rules = {
  content: {
    required: helpers.withMessage(
      t('notes_menu.rules.content.non_empty').toString(),
      required
    )
  }
};

const v$ = setValidation(
  rules,
  { content: computed(() => get(value).content) },
  { $autoDirty: true }
);
</script>

<template>
  <VForm :value="valid" class="pt-2">
    <div>
      <VTextField
        :value="value.title"
        outlined
        :placeholder="t('notes_menu.labels.title')"
        @input="input({ title: $event })"
      />
    </div>
    <div>
      <VTextarea
        :value="value.content"
        outlined
        :placeholder="t('notes_menu.labels.content')"
        :error-messages="toMessages(v$.content)"
        @input="input({ content: $event })"
      />
    </div>
  </VForm>
</template>
