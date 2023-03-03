<script setup lang="ts">
import { useListeners } from 'vue';

const rootAttrs = useAttrs();
const rootListeners = useListeners();

withDefaults(
  defineProps<{
    value?: string | null;
    outlined?: boolean;
    hint?: string;
    prependIcon?: string;
    sensitiveKey?: boolean;
  }>(),
  {
    value: null,
    outlined: false,
    hint: '',
    prependIcon: 'mdi-key',
    sensitiveKey: false
  }
);

const emit = defineEmits<{ (e: 'input', value: string | null): void }>();

const revealed = ref(false);
const input = (value: string | null) => {
  emit('input', value);
};
</script>

<template>
  <v-text-field
    v-bind="rootAttrs"
    :value="value"
    :prepend-icon="outlined ? null : prependIcon"
    :prepend-inner-icon="outlined ? prependIcon : null"
    :type="revealed ? 'text' : 'password'"
    :class="{
      'sensitive-key': sensitiveKey
    }"
    :hint="hint"
    :persistent-hint="!!hint"
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

<style scoped lang="scss">
.sensitive-key {
  &.v-input {
    &--is-disabled {
      :deep(.v-icon),
      :deep(.v-label) {
        color: green !important;
      }
    }
  }
}
</style>
