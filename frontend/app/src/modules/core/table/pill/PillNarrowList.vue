<script setup lang="ts">
import type { NarrowSuggestion } from '@/modules/core/table/pill/core/narrowing';
import PillValueIcon from '@/modules/core/table/pill/PillValueIcon.vue';
import EvmChainIcon from '@/modules/shell/components/EvmChainIcon.vue';

const { suggestions, highlighted = 0, emptyText = '', loading = false } = defineProps<{
  /** Cross-field narrowing results for what the user typed in the bar. */
  suggestions: NarrowSuggestion[];
  /** Index of the keyboard-highlighted row; the bar owns it, since the input lives there. */
  highlighted?: number;
  emptyText?: string;
  /** An asset search is still running; its rows will be appended to what is already shown. */
  loading?: boolean;
}>();

const emit = defineEmits<{
  'select': [suggestion: NarrowSuggestion];
  'update:highlighted': [index: number];
}>();

function keyOf(suggestion: NarrowSuggestion): string {
  if (suggestion.kind === 'field')
    return `field-${suggestion.field.key}`;
  // A filter row is identified by its operator: one query can offer the same field twice (a bare
  // number means either bound), so the field key alone would collide.
  if (suggestion.kind === 'filter')
    return `filter-${suggestion.field.key}-${suggestion.filter.op}`;
  return `value-${suggestion.field.key}-${suggestion.value}`;
}

// The list scrolls past its max height, and the bar drives the highlight from the input with the
// arrow keys, so the highlighted row has to be brought into view here — nothing else can. `nearest`
// scrolls the list by the minimum needed and leaves the page alone.
const rows = useTemplateRef<HTMLButtonElement[]>('rows');

// Hovering moves the highlight too, and scrolling then pulls the list out from under the cursor,
// which lands a different row under it and moves the highlight again. The bar owns the highlight,
// so the source is not visible here — but the pointer changes are the ones this list emits, so
// flagging them on the way out identifies them when they come back as a prop.
let fromPointer = false;

function highlightFromPointer(index: number): void {
  fromPointer = true;
  emit('update:highlighted', index);
}

watch(() => highlighted, (index) => {
  if (fromPointer) {
    fromPointer = false;
    return;
  }
  get(rows)?.[index]?.scrollIntoView({ block: 'nearest' });
});
</script>

<template>
  <div class="flex flex-col gap-0.5 p-1.5 min-w-[16rem] max-w-[20rem] max-h-[17rem] overflow-y-auto">
    <button
      v-for="(suggestion, index) in suggestions"
      :id="`pill-narrow-row-${index}`"
      :key="keyOf(suggestion)"
      ref="rows"
      type="button"
      role="menuitem"
      class="flex items-center gap-2.5 w-full px-2.5 py-1.5 rounded-md text-sm text-left transition-colors"
      :class="index === highlighted
        ? 'bg-rui-primary/10 text-rui-primary'
        : 'text-rui-text-primary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800'"
      data-testid="pill-narrow-row"
      :data-key="keyOf(suggestion)"
      @mousemove="highlightFromPointer(index)"
      @click="emit('select', suggestion)"
    >
      <!-- A value row carries the same icon its pill will: the asset's mark up front, its chain
           after it, so `USDC` on five chains reads as five distinct rows. -->
      <PillValueIcon
        v-if="suggestion.kind === 'value' && (suggestion.field.display || suggestion.field.resolveIcon || suggestion.field.resolveSwatch)"
        :display="suggestion.field.display"
        :icon="suggestion.field.resolveIcon?.(suggestion.value)"
        :swatch="suggestion.field.resolveSwatch?.(suggestion.value)"
        :value="suggestion.value"
        size="18px"
      />
      <span class="flex-1 min-w-0 truncate">
        {{ suggestion.label }}
        <span
          v-if="suggestion.kind === 'value' && suggestion.caption"
          class="text-rui-text-secondary"
        >
          {{ suggestion.caption }}
        </span>
      </span>
      <EvmChainIcon
        v-if="suggestion.kind === 'value' && suggestion.chain"
        :chain="suggestion.chain"
        size="14px"
        tooltip
      />
      <!-- A value or a read-out filter is tagged with the field it belongs to, so `ETH` reads as
           an Asset value and `greater than 100` as an Amount one. A field row needs no tag: its
           label already is the field. -->
      <span
        v-if="suggestion.kind !== 'field'"
        class="text-xs text-rui-text-secondary shrink-0"
      >
        {{ suggestion.field.label }}
      </span>
    </button>
    <!-- Announced: asset rows are appended when a remote search returns, so without a live region
         nothing tells a screen reader the list grew under it. -->
    <div
      v-if="loading"
      class="flex justify-center py-2"
      role="status"
      aria-live="polite"
      data-testid="pill-narrow-loading"
    >
      <RuiProgress
        circular
        variant="indeterminate"
        size="16"
        color="primary"
      />
    </div>
    <div
      v-else-if="suggestions.length === 0"
      class="text-rui-text-secondary text-sm px-2.5 py-3 text-center"
      role="status"
      aria-live="polite"
      data-testid="pill-narrow-empty"
    >
      {{ emptyText }}
    </div>
  </div>
</template>
