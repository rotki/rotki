<script setup lang="ts">
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

const highlighted = ref<number>(0);

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

// Selected values pinned above the list as chips, so the choice stays visible once it scrolls away.
const labelByValue = computed<Map<string, string>>(() => new Map(options.map(option => [option.value, option.label])));
const selectedChips = computed<SelectOption[]>(() =>
  get(selected).map(value => ({ label: get(labelByValue).get(value) ?? value, value })),
);

// Virtualize the rows: option lists (protocols, assets, …) can run to hundreds of entries.
const { containerProps, list, scrollTo, wrapperProps } = useVirtualList(filtered, { itemHeight: ITEM_HEIGHT, overscan: 8 });

// The first row the highlight may land on: past any pinned rows, unless they are all there is.
const firstSelectable = computed<number>(() => (pinned < get(filtered).length ? pinned : 0));

// Order-independent, so pinning a selection to the top never reads as a new list.
const filteredValues = computed<string>(() => [...get(filtered).map(option => option.value)].sort().join(','));

// Virtualized, so the highlight has to be scrolled to as well or it lands off screen.
watch(filteredValues, () => {
  set(highlighted, get(firstSelectable));
  scrollTo(get(highlighted));
});

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

// A wheel scroll slides rows under a stationary cursor and still reports a mousemove.
let lastX = Number.NaN;
let lastY = Number.NaN;

function onPointerMove(event: MouseEvent, index: number): void {
  if (event.clientX === lastX && event.clientY === lastY)
    return;

  lastX = event.clientX;
  lastY = event.clientY;
  set(highlighted, index);
}

/**
 * Drives the list from the keyboard: dismiss, move the highlight, commit a row.
 *
 * @remarks
 * Escape is handled here rather than left to the surrounding menu, and before anything else. The
 * menu can only dismiss itself while its own content holds focus, and this list is what holds it;
 * an empty list has to be dismissable too, so the check cannot sit behind the row count.
 *
 * A composing IME is left alone. Mid-word, Enter confirms the candidate and the arrows walk the
 * candidate list, so acting on them commits a row and closes the list under the user.
 */
function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    emit('close');
    return;
  }

  if (event.isComposing)
    return;

  const items = get(filtered);
  if (items.length === 0)
    return;
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    set(highlighted, (get(highlighted) + 1) % items.length);
    scrollTo(get(highlighted));
  }
  else if (event.key === 'ArrowUp') {
    event.preventDefault();
    set(highlighted, (get(highlighted) - 1 + items.length) % items.length);
    scrollTo(get(highlighted));
  }
  else if (event.key === 'Enter') {
    event.preventDefault();
    toggle(items[get(highlighted)].value);
  }
}
</script>

<template>
  <div class="flex flex-col w-[20rem]">
    <!-- Only for multi-select: a scrolled long list needs the selections summarised. A single-select
      field would just echo its one checked row (and the bar pill), reading as a confusing mini-pill. -->
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
        <span class="truncate max-w-[9rem]">{{ chip.label }}</span>
        <RuiIcon
          name="lu-x"
          size="12"
          class="shrink-0"
        />
      </button>
    </div>

    <!-- The focus ring lives on this row, not the input: the input is borderless by design, so its
         `outline-none` needs a replacement somewhere, and the row is what reads as the field. -->
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
      v-bind="containerProps"
      class="max-h-[15rem] p-1"
    >
      <div v-bind="wrapperProps">
        <button
          v-for="item in list"
          :key="item.data.value"
          type="button"
          class="flex items-center gap-2.5 w-full px-2.5 h-8 rounded-md text-sm text-left transition-colors"
          :class="item.index === highlighted
            ? 'bg-rui-primary/10'
            : 'hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800'"
          role="menuitemcheckbox"
          :aria-checked="selectedSet.has(item.data.value)"
          data-testid="value-select-option"
          :data-key="item.data.value"
          @mousemove="onPointerMove($event, item.index)"
          @click="toggle(item.data.value)"
        >
          <!-- aria-checked on the row already states selection, so the indicator is decorative to
               assistive tech and would otherwise be read twice. -->
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
    <!-- Announced: the rows arrive from a remote search, so without a live region a screen reader
         is told nothing between typing and results appearing. -->
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
