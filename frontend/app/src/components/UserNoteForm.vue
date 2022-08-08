<template>
  <v-form :value="valid" class="pt-2">
    <div>
      <v-text-field
        :value="value.title"
        outlined
        :placeholder="$t('notes_menu.labels.title')"
        @input="input({ title: $event })"
      />
    </div>
    <div>
      <v-textarea
        :value="value.content"
        outlined
        :placeholder="$t('notes_menu.labels.content')"
        :error-messages="v$.content.$errors.map(e => e.$message)"
        @input="input({ content: $event })"
      />
    </div>
  </v-form>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { useValidation } from '@/composables/validation';
import i18n from '@/i18n';
import { UserNote } from '@/types/notes';

export default defineComponent({
  name: 'UserNoteForm',
  props: {
    value: {
      required: true,
      type: Object as PropType<Partial<UserNote>>
    }
  },
  emits: ['input', 'valid'],
  setup(props, { emit }) {
    const { value } = toRefs(props);

    const valid = ref(false);

    const input = (newInput: Partial<UserNote>) => {
      emit('input', { ...get(value), ...newInput });
    };

    const rules = {
      content: {
        required: helpers.withMessage(
          i18n.t('notes_menu.rules.content.non_empty').toString(),
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

    const { callIfValid } = useValidation(v$);

    return {
      valid,
      rules,
      v$,
      callIfValid,
      input
    };
  }
});
</script>
