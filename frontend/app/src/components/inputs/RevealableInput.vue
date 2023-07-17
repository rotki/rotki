<script setup lang="ts">
import { useListeners } from 'vue';

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
const rootAttrs = useAttrs();
const rootListeners = useListeners();

const revealed = ref(false);
const input = (value: string | null) => {
  emit('input', value);
};
</script>

<template>
  <VTextField
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
    @input="input($event)"
  >
    <template #append>
      <VIcon v-if="revealed" tabindex="-1" @click="revealed = !revealed">
        mdi-eye
      </VIcon>
      <VIcon v-else tabindex="-1" @click="revealed = !revealed">
        mdi-eye-off
      </VIcon>
    </template>
  </VTextField>
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
