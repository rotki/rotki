<template>
  <v-text-field
    v-bind="rootAttrs"
    :value="value"
    :prepend-icon="outlined ? null : prependIcon"
    :prepend-inner-icon="outlined ? prependIcon : null"
    :type="revealed ? 'text' : 'password'"
    :rules="rules"
    :label="label"
    :hint="hint"
    :disabled="disabled"
    :persistent-hint="!!hint"
    :error-messages="errorMessages"
    :outlined="outlined"
    single-line
    v-on="rootListeners"
    @input="input"
  >
    <template #append>
      <v-icon v-if="revealed" tabindex="-1" @click="revealed = !revealed">
        mdi-eye
      </v-icon>
      <v-icon v-else tabindex="-1" @click="revealed = !revealed">
        mdi-eye-off
      </v-icon>
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
import { PropType, ref, useAttrs, useListeners } from 'vue';

const rootAttrs = useAttrs();
const rootListeners = useListeners();

defineProps({
  value: {
    required: false,
    type: String as PropType<string | null>,
    default: null
  },
  rules: {
    required: false,
    default: () => [],
    type: Array as PropType<((v: string) => boolean | string)[]>
  },
  outlined: {
    required: false,
    type: Boolean,
    default: false
  },
  disabled: {
    required: false,
    type: Boolean,
    default: false
  },
  label: {
    required: false,
    type: String,
    default: ''
  },
  hint: {
    required: false,
    type: String,
    default: ''
  },
  prependIcon: {
    required: false,
    type: String,
    default: 'mdi-key'
  },
  errorMessages: {
    required: false,
    type: [String, Array],
    default: ''
  }
});

const emit = defineEmits<{ (e: 'input', value: string | null): void }>();

const revealed = ref(false);
const input = (value: string | null) => {
  emit('input', value);
};
</script>
