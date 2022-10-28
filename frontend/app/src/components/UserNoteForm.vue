<template>
  <v-form :value="valid" class="pt-2">
    <div>
      <v-text-field
        :value="value.title"
        outlined
        :placeholder="t('notes_menu.labels.title')"
        @input="input({ title: $event })"
      />
    </div>
    <div>
      <v-textarea
        :value="value.content"
        outlined
        :placeholder="t('notes_menu.labels.content')"
        :error-messages="v$.content.$errors.map(e => e.$message)"
        @input="input({ content: $event })"
      />
    </div>
  </v-form>
</template>
<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { PropType } from 'vue';
import { UserNote } from '@/types/notes';

const props = defineProps({
  value: {
    required: true,
    type: Object as PropType<Partial<UserNote>>
  }
});

const emit = defineEmits(['input', 'valid']);

const { t } = useI18n();
const { value } = toRefs(props);

const valid = ref(false);

const input = (newInput: Partial<UserNote>) => {
  emit('input', { ...get(value), ...newInput });
};

const rules = {
  content: {
    required: helpers.withMessage(
      t('notes_menu.rules.content.non_empty').toString(),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  { content: computed(() => get(value).content) },
  { $autoDirty: true }
);

watch(v$, ({ $invalid }) => {
  set(valid, !$invalid);
  emit('valid', get(valid));
});
</script>
