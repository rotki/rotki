<script setup lang="ts">
import JsonEditorVue from 'json-editor-vue';

const props = withDefaults(
  defineProps<{
    label?: string;
    value: object;
  }>(),
  {
    label: ''
  }
);

const emit = defineEmits<{
  (e: 'input', newValue: object): void;
}>();

const { value } = toRefs(props);

const model = computed({
  get() {
    return get(value);
  },
  set(value: object) {
    emit('input', value);
  }
});

const css = useCssModule();
</script>

<template>
  <div class="mt-4">
    <div v-if="label" class="text-caption text-rui-text-secondary mb-1">
      {{ label }}
    </div>
    <div :class="css.editor">
      <JsonEditorVue v-model="model" :navigation-bar="false" />
    </div>
  </div>
</template>

<style lang="scss" module>
.editor {
  --jse-background-color: transparent;
  --jse-main-border: none;
  --jse-theme-color: rgb(var(--rui-light-primary-main));

  @apply rounded border border-rui-grey-500;
}

:global(.dark) {
  .editor {
    --jse-theme-color: rgb(var(--rui-dark-primary-main));
    --jse-delimiter-color: var(--rui-dark-text-secondary);
    --jse-text-color: var(--rui-dark-text-secondary);
    --jse-key-color: var(--rui-dark-text-secondary);
    --jse-tag-color: var(--rui-dark-text-secondary);
    --jse-tag-background: var(--rui-dark-text-secondary);

    @apply border-rui-grey-700;
  }
}
</style>
