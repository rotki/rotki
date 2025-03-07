<script setup lang="ts">
import type { UserNote } from '@/types/notes';
import { useFormStateWatcher } from '@/composables/form';
import { refOptional, useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const modelValue = defineModel<Partial<UserNote>>({ required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n();

const title = refOptional(useRefPropVModel(modelValue, 'title'), '');
const content = refOptional(useRefPropVModel(modelValue, 'content'), '');

const rules = {
  content: {
    required: helpers.withMessage(t('notes_menu.rules.content.non_empty'), required),
  },
  title: {},
};

const states = { content, title };

const v$ = useVuelidate(rules, states, { $autoDirty: true });

useFormStateWatcher(states, stateUpdated);

defineExpose({
  validate: () => get(v$).$validate(),
});
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
