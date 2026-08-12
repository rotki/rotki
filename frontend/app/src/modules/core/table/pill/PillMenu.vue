<script setup lang="ts">
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { FilterValueTypes } from '@/modules/core/table/filtering';

const { fields, searchPlaceholder = '', emptyText = '' } = defineProps<{
  /** The fields offered to add (typically the ones without an active filter). */
  fields: FieldDef[];
  searchPlaceholder?: string;
  emptyText?: string;
}>();

const emit = defineEmits<{
  select: [field: FieldDef];
}>();

const { t } = useI18n({ useScope: 'global' });

const search = ref<string>('');
const highlighted = ref<number>(0);

// Keyboard-shortcut glyphs for the footer (symbols/key names, not translatable copy).
const keyHints = ['↑', '↓', '↵', 'esc'];

// The menu mounts fresh each time it opens, so focus its search on mount: clicking
// `+ Add filter` lands the caret in the field search, ready to narrow by typing.
const searchField = useTemplateRef<HTMLInputElement>('searchField');

onMounted(async () => {
  await nextTick();
  get(searchField)?.focus();
});

const filtered = computed<FieldDef[]>(() => {
  const query = get(search).toLowerCase().trim();
  if (!query)
    return fields;
  return fields.filter(field => field.label.toLowerCase().includes(query));
});

// Keep the highlight in range as the list narrows while typing.
watch(filtered, () => set(highlighted, 0));

// The list scrolls past its height and the arrow keys are handled on the search box, so nothing
// else can bring the highlighted row back into view: without this the highlight walks off the
// bottom and the user is arrowing through rows they cannot see. `nearest` scrolls the list by the
// least it can and leaves the page alone.
const rows = useTemplateRef<HTMLButtonElement[]>('rows');

// Scrolled from the key handler rather than from a watcher on the highlight: hovering also moves
// the highlight, and scrolling then pulls the list out from under the cursor, which lands a
// different row under it and moves the highlight again. Only the keyboard needs to chase a row
// that is out of sight.
function scrollToHighlighted(): void {
  get(rows)?.[get(highlighted)]?.scrollIntoView({ block: 'nearest' });
}

// A short, muted kind label on the right of a row for the non-plain fields, so range/date/asset
// pills read as more than a name. Plain text (enum) rows show nothing.
function metaFor(field: FieldDef): string {
  switch (field.valueType) {
    case FilterValueTypes.ASSET:
      return t('table_filter.field_kinds.asset');
    case FilterValueTypes.DATE:
      return t('table_filter.field_kinds.date');
    case FilterValueTypes.RANGE:
      return t('table_filter.field_kinds.range');
    case FilterValueTypes.BOOLEAN:
      return t('table_filter.field_kinds.toggle');
    default:
      return '';
  }
}

// Arrow keys move the highlight, Enter picks it, so the whole flow is keyboard-only:
// focus the search (auto), type to narrow, arrow to the field, Enter to add it.
function onKeydown(event: KeyboardEvent): void {
  const items = get(filtered);
  if (items.length === 0)
    return;
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    set(highlighted, (get(highlighted) + 1) % items.length);
    scrollToHighlighted();
  }
  else if (event.key === 'ArrowUp') {
    event.preventDefault();
    set(highlighted, (get(highlighted) - 1 + items.length) % items.length);
    scrollToHighlighted();
  }
  else if (event.key === 'Enter') {
    event.preventDefault();
    emit('select', items[get(highlighted)]);
  }
}
</script>

<template>
  <div class="flex flex-col min-w-[16rem] max-w-[20rem]">
    <!-- The focus ring lives on this row rather than the input: the input is borderless by design,
         so `outline-none` there needs a replacement somewhere, and the row is what reads as the
         field. Same pattern as the bar's container. -->
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
        class="flex-1 min-w-0 bg-transparent py-2.5 text-sm text-rui-text-primary outline-none placeholder:text-rui-text-secondary"
        :placeholder="searchPlaceholder"
        :aria-label="searchPlaceholder"
        autocomplete="off"
        spellcheck="false"
        data-testid="pill-menu-search"
        @keydown="onKeydown($event)"
      />
    </div>

    <div class="flex flex-col gap-0.5 p-1.5 max-h-[17rem] overflow-y-auto">
      <button
        v-for="(field, index) in filtered"
        :key="field.key"
        ref="rows"
        type="button"
        role="menuitem"
        class="flex items-center gap-2.5 w-full px-2.5 py-1.5 rounded-md text-sm text-left transition-colors"
        :class="index === highlighted
          ? 'bg-rui-primary/10 text-rui-primary'
          : 'text-rui-text-primary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800'"
        data-testid="pill-menu-field"
        :data-field="field.key"
        @mousemove="highlighted = index"
        @click="emit('select', field)"
      >
        <span class="flex-1 truncate">
          {{ field.label }}
        </span>
        <span
          v-if="metaFor(field)"
          class="text-xs text-rui-text-secondary shrink-0"
        >
          {{ metaFor(field) }}
        </span>
      </button>
      <div
        v-if="filtered.length === 0"
        class="text-rui-text-secondary text-sm px-2.5 py-3 text-center"
        role="status"
        aria-live="polite"
        data-testid="pill-menu-empty"
      >
        {{ emptyText }}
      </div>
    </div>

    <div class="flex items-center gap-1.5 px-3 py-1.5 border-t border-rui-grey-200 dark:border-rui-grey-700 text-xs text-rui-text-secondary">
      <kbd
        v-for="hint in keyHints"
        :key="hint"
        class="px-1 rounded border border-rui-grey-300 dark:border-rui-grey-600 font-mono text-[10px] leading-4"
      >
        {{ hint }}
      </kbd>
    </div>
  </div>
</template>
