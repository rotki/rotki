<script setup lang="ts">
import type { Content, JsonEditor } from 'vanilla-jsoneditor';
import { debounce } from 'es-toolkit';

const modelValue = defineModel<Record<string, any>>({ required: true });

const {
  label = '',
} = defineProps<{
  label?: string;
}>();

const jsonEditor = ref<JsonEditor>();
const jsonEditorContainer = useTemplateRef<HTMLDivElement>('jsonEditorContainer');

watch(modelValue, (newValue: any) => {
  const jsonEditorVal = get(jsonEditor);
  if (jsonEditorVal)
    jsonEditorVal.set([undefined, ''].includes(newValue) ? { text: '' } : { json: newValue });
}, {
  deep: true,
});

onMounted(async () => {
  const container = get(jsonEditorContainer);
  if (!container)
    return;

  // Pulled from the dynamic import so the editor stays out of the eager bundle.
  const { createJSONEditor, isTextContent } = await import('vanilla-jsoneditor');

  const onChange = debounce((updatedContent: Content) => {
    set(modelValue, isTextContent(updatedContent) ? updatedContent.text : updatedContent.json);
  }, 100);

  const newJsonEditor = createJSONEditor({
    props: {
      content: {
        json: get(modelValue),
      },
      navigationBar: false,
      onChange,
    },
    target: container,
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
