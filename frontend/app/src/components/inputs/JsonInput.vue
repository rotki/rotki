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
    <div class="json-editor rounded border border-rui-grey-500 dark:border-rui-grey-700">
      <div ref="jsonEditorContainer" />
    </div>
  </div>
</template>
