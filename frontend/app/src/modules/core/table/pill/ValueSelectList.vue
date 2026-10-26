<script setup lang="ts">
import { useListHighlight } from '@/modules/core/common/use-list-highlight';

export interface SelectOption {
  value: string;
  label: string;
  /** Muted secondary text shown after the label (e.g. an account's address under its name). */
  caption?: string;
  /** Extra text matched by the search box beyond the label (e.g. an account's address/tags). */
  keywords?: string;
  /** While true the label renders as a skeleton (e.g. an account's ENS name still resolving). */
  loading?: boolean;
}

const selected = defineModel<string[]>({ required: true });
// The search text is a model so an async list (e.g. assets) can drive a remote search from it.
const search = defineModel<string>('search', { default: '' });

const { options, multiple = false, searchPlaceholder = '', emptyText = '', noFilter = false, loading = false, pinned = 0 } = defineProps<{
  options: SelectOption[];
  multiple?: boolean;
  searchPlaceholder?: string;
  emptyText?: string;
  /** Skip local label/keyword filtering because the options are already filtered remotely. */
  noFilter?: boolean;
  /** Show a spinner in the search row while an async list is fetching. */
  loading?: boolean;
  /**
   * How many leading options are pinned rather than search results (the asset list pins what is
   * already selected). They keep their place in the list but never take the initial highlight, so
   * typing and pressing enter picks the first *result* instead of re-toggling the pinned value.
   */
  pinned?: number;
}>();

const emit = defineEmits<{
  /** Escape was pressed: the list is done, so whatever opened it can close. */
  close: [];
}>();

defineSlots<{
  /** Optional leading icon/avatar for an option, rendered from its value. */
  icon?: (props: { value: string }) => any;
}>();

const ITEM_HEIGHT = 32;

const searchField = useTemplateRef<HTMLInputElement>('searchField');

onMounted(async () => {
  await nextTick();
  get(searchField)?.focus();
});

const filtered = computed<SelectOption[]>(() => {
  const query = get(search).toLowerCase().trim();
  if (noFilter || !query)
    return options;
  // Lowercased here, not trusted from the producer: raw keywords (a checksummed address) never match.
  return options.filter(option =>
    option.label.toLowerCase().includes(query) || (option.keywords?.toLowerCase().includes(query) ?? false),
  );
});

const selectedSet = computed<Set<string>>(() => new Set(get(selected)));

const listId = useId();

function rowId(index: number): string {
  return `${listId}-${index}`;
}

// Selected values pinned above the list as chips, so the choice stays visible once it scrolls away.
const labelByValue = computed<Map<string, string>>(() => new Map(options.map(option => [option.value, option.label])));
const selectedChips = computed<SelectOption[]>(() =>
  get(selected).map(value => ({ label: get(labelByValue).get(value) ?? value, value })),
);

// Virtualize the rows: option lists (protocols, assets, …) can run to hundreds of entries.
const { containerProps, list, scrollTo, wrapperProps } = useVirtualList(filtered, { itemHeight: ITEM_HEIGHT, overscan: 8 });

const { highlighted, onKeydown, onPointerMove } = useListHighlight(filtered, {
  firstSelectable: () => pinned,
  keyOf: option => option.value,
  onClose: () => emit('close'),
  onSelect: option => toggle(option.value),
  scrollTo,
});

/** The row the search field names as active, so a screen reader follows the arrow keys. */
const activeRowId = computed<string | undefined>(() =>
  get(filtered).length > 0 ? rowId(get(highlighted)) : undefined);

/**
 * Picks a row's indicator icon: checkbox squares when several values may be held, circles otherwise.
 *
 * @remarks
 * A checkbox on a single-choice field wrongly implies several values can be ticked at once.
 */
function indicatorIcon(selected: boolean): string {
  if (multiple)
    return selected ? 'lu-square-check' : 'lu-square';
  return selected ? 'lu-circle-check' : 'lu-circle';
}

function toggle(value: string): void {
  const current = get(selected);
  if (multiple) {
    set(selected, get(selectedSet).has(value) ? current.filter(item => item !== value) : [...current, value]);
  }
  else {
    // Single select: picking the active value clears it, otherwise it becomes the only value.
    set(selected, get(selectedSet).has(value) ? [] : [value]);
  }
}
</script>

<template>
  <div class="flex flex-col w-80">
    <div
      v-if="multiple && selectedChips.length > 0"
      class="flex flex-wrap gap-1 p-2 border-b border-rui-grey-200 dark:border-rui-grey-700"
    >
      <button
        v-for="chip in selectedChips"
        :key="chip.value"
        type="button"
        class="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-full bg-rui-primary/10 text-xs text-rui-primary hover:bg-rui-primary/20"
        data-testid="value-select-chip"
        :data-key="chip.value"
        @click="toggle(chip.value)"
      >
        <span class="truncate max-w-36">{{ chip.label }}</span>
        <RuiIcon
          name="lu-x"
          size="12"
          class="shrink-0"
        />
      </button>
    </div>

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
        :placeholder="searchPlaceholder"
        :aria-label="searchPlaceholder"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded="true"
        :aria-controls="listId"
        :aria-activedescendant="activeRowId"
        autocomplete="off"
        spellcheck="false"
        data-testid="value-select-search"
        @keydown="onKeydown($event)"
      />
      <RuiProgress
        v-if="loading"
        class="shrink-0"
        color="primary"
        circular
        variant="indeterminate"
        size="16"
        thickness="2"
        data-testid="value-select-loading"
      />
    </div>

    <div
      v-if="filtered.length > 0"
      :id="listId"
      v-bind="containerProps"
      class="max-h-60 p-1"
      role="listbox"
      :aria-multiselectable="multiple"
      :aria-label="searchPlaceholder"
    >
      <div v-bind="wrapperProps">
        <button
          v-for="item in list"
          :id="rowId(item.index)"
          :key="item.data.value"
          type="button"
          class="flex items-center gap-2.5 w-full px-2.5 h-8 rounded-md text-sm text-left transition-colors"
          :class="item.index === highlighted
            ? 'bg-rui-primary/10'
            : 'hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800'"
          role="option"
          :aria-selected="selectedSet.has(item.data.value)"
          data-testid="value-select-option"
          :data-key="item.data.value"
          @mousemove="onPointerMove($event, item.index)"
          @click="toggle(item.data.value)"
        >
          <RuiIcon
            class="shrink-0"
            :class="selectedSet.has(item.data.value) ? 'text-rui-primary' : 'text-rui-text-secondary opacity-40'"
            :name="indicatorIcon(selectedSet.has(item.data.value))"
            size="16"
            aria-hidden="true"
          />
          <slot
            name="icon"
            :value="item.data.value"
          />
          <RuiSkeletonLoader
            v-if="item.data.loading"
            type="text"
            class="w-[4ch]"
          />
          <span
            v-else
            class="flex-1 min-w-0 flex items-baseline gap-1.5 truncate"
          >
            <span class="truncate text-rui-text-primary">{{ item.data.label }}</span>
            <span
              v-if="item.data.caption"
              class="truncate font-mono text-xs text-rui-text-secondary"
            >
              {{ item.data.caption }}
            </span>
          </span>
        </button>
      </div>
    </div>
    <div
      v-else-if="loading"
      class="flex items-center justify-center px-2.5 py-4"
      role="status"
      aria-live="polite"
      data-testid="value-select-loading-empty"
    >
      <RuiProgress
        color="primary"
        circular
        variant="indeterminate"
        size="20"
        thickness="2"
      />
    </div>
    <div
      v-else
      class="text-rui-text-secondary text-sm px-2.5 py-3 text-center"
      role="status"
      aria-live="polite"
      data-testid="value-select-empty"
    >
      {{ emptyText }}
    </div>
  </div>
</template>
