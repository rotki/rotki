<script setup lang="ts">
import {
  type Content,
  type JSONContent,
  JSONEditor,
  type TextContent
} from 'vanilla-jsoneditor';
import { debounce } from 'lodash-es';

const props = withDefaults(
  defineProps<{
    label?: string;
    value: Record<string, any>;
  }>(),
  {
    label: ''
  }
);

const emit = defineEmits<{
  (e: 'input', newValue: any): void;
}>();

const { value } = toRefs(props);

const css = useCssModule();

const jsonEditorContainer = ref();
const jsonEditor: Ref<JSONEditor | null> = ref(null);

onMounted(() => {
  const onChange = debounce((updatedContent: Content) => {
    emit(
      'input',
      (updatedContent as TextContent).text === undefined
        ? (updatedContent as JSONContent).json
        : (updatedContent as TextContent).text
    );
  }, 100);

  const newJsonEditor = new JSONEditor({
    target: get(jsonEditorContainer),
    props: {
      content: {
        json: get(value)
      },
      navigationBar: false,
      onChange
    }
  });

  set(jsonEditor, newJsonEditor);
});

watch(
  value,
  (newValue: any) => {
    const jsonEditorVal = get(jsonEditor);
    if (jsonEditorVal) {
      jsonEditorVal.set(
        [undefined, ''].includes(newValue) ? { text: '' } : { json: newValue }
      );
    }
  },
  {
    deep: true
  }
);

onBeforeUnmount(() => {
  const jsonEditorVal = get(jsonEditor);

  if (jsonEditorVal) {
    jsonEditorVal.destroy();
  }
});
</script>

<template>
  <div class="mt-4">
    <div v-if="label" class="text-caption text-rui-text-secondary mb-1">
      {{ label }}
    </div>
    <div :class="css.editor">
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
