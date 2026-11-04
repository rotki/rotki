<script setup lang="ts">
/**
 * The search row of a pill popover list: a combobox input that filters the list below it.
 *
 * @remarks
 * It takes the focus when it mounts. The popovers mount fresh on every open, so the caret is ready
 * to type, and `autofocus` alone is ignored for an input inserted into an already-loaded document.
 * Arrow and Enter keys are re-emitted for the parent, which owns the highlighted row.
 */
const search = defineModel<string>({ required: true });

const { placeholder, listId, activeRowId, testId } = defineProps<{
  placeholder: string;
  /** Id of the listbox the input controls. */
  listId: string;
  /** Id of the highlighted row, so a screen reader follows the arrow keys. */
  activeRowId?: string;
  testId: string;
}>();

const emit = defineEmits<{
  keydown: [event: KeyboardEvent];
}>();

defineSlots<{
  /** Trailing content of the row, such as a loading spinner. */
  append?: () => any;
}>();

const searchField = useTemplateRef<HTMLInputElement>('searchField');

onMounted(async () => {
  await nextTick();
  get(searchField)?.focus();
});
</script>

<template>
  <div class="flex items-center gap-2 px-3 border-b transition-colors border-rui-grey-200 dark:border-rui-grey-700 focus-within:border-rui-primary dark:focus-within:border-rui-primary">
    <RuiIcon
      name="lu-search"
      size="16"
      class="text-rui-text-secondary shrink-0"
      aria-hidden="true"
    />
    <input
      ref="searchField"
      v-model="search"
      type="text"
      class="flex-1 min-w-0 bg-transparent py-2.5 text-sm text-rui-text-primary outline-hidden placeholder:text-rui-text-secondary"
      :placeholder="placeholder"
      :aria-label="placeholder"
      role="combobox"
      aria-autocomplete="list"
      aria-expanded="true"
      :aria-controls="listId"
      :aria-activedescendant="activeRowId"
      autocomplete="off"
      spellcheck="false"
      :data-testid="testId"
      @keydown="emit('keydown', $event)"
    />
    <slot name="append" />
  </div>
</template>
