<script setup lang="ts">
import { assert } from '@rotki/common';
import { debounce } from 'es-toolkit';
import { type Content, createJSONEditor, type JSONContent, type JsonEditor, type TextContent } from 'vanilla-jsoneditor';

const modelValue = defineModel<Record<string, any>>({ required: true });

withDefaults(defineProps<{
  label?: string;
}>(), {
  label: '',
});

const jsonEditor = ref<JsonEditor>();
const jsonEditorContainer = useTemplateRef<HTMLDivElement>('jsonEditorContainer');

watch(modelValue, (newValue: any) => {
  const jsonEditorVal = get(jsonEditor);
  if (jsonEditorVal)
    jsonEditorVal.set([undefined, ''].includes(newValue) ? { text: '' } : { json: newValue });
}, {
  deep: true,
});

onMounted(() => {
  const onChange = debounce((updatedContent: Content) => {
    set(modelValue, (updatedContent as TextContent).text === undefined
      ? (updatedContent as JSONContent).json
      : (updatedContent as TextContent).text);
  }, 100);

  assert(isDefined(jsonEditorContainer));

  const newJsonEditor = createJSONEditor({
    props: {
      content: {
        json: get(modelValue),
      },
      navigationBar: false,
      onChange,
    },
    target: get(jsonEditorContainer),
  });

  set(jsonEditor, newJsonEditor);
});

onBeforeUnmount(() => {
  get(jsonEditor)?.destroy();
});
</script>

<template>
  <div class="mt-4">
    <div
      v-if="label"
      class="text-caption text-rui-text-secondary mb-1"
    >
      {{ label }}
    </div>
    <div :class="$style.editor">
      <div ref="jsonEditorContainer" />
    </div>
  </div>
</template>

<style lang="scss" module>
.editor {
  @apply rounded border border-rui-grey-500;

  --jse-background-color: transparent;
  --jse-main-border: none;
  --jse-theme-color: rgb(var(--rui-light-primary-main));
}

:global(.dark) {
  .editor {
    @apply border-rui-grey-700;

    --jse-theme-color: rgb(var(--rui-dark-primary-main));
    --jse-delimiter-color: var(--rui-dark-text-secondary);
    --jse-text-color: var(--rui-dark-text-secondary);
    --jse-key-color: var(--rui-dark-text-secondary);
    --jse-tag-color: var(--rui-dark-text-secondary);
    --jse-tag-background: var(--rui-dark-text-secondary);
  }
}
</style>
