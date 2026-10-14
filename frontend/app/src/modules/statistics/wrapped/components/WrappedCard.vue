<script setup lang="ts" generic="T extends object">
const { items, ranked = true, weight } = defineProps<{
  items: T[];
  /** Number the rows, for lists sorted by their value. */
  ranked?: boolean;
  /** A row's size; given, each row draws a bar against the largest, so the list compares at a glance. */
  weight?: (item: T) => number;
}>();

defineSlots<{
  'header-icon': () => any;
  'header': () => any;
  'label': (props: { item: T; index: number }) => any;
  'value': (props: { item: T; index: number }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const INITIAL_LENGTH = 5;

const showAll = ref<boolean>(false);

const hasMore = computed<boolean>(() => items.length > INITIAL_LENGTH);

const visibleItems = computed<T[]>(() => (get(showAll) ? items : items.slice(0, INITIAL_LENGTH)));

const largest = computed<number>(() => (weight ? Math.max(0, ...items.map(weight)) : 0));

function barWidth(item: T): string | undefined {
  const max = get(largest);
  if (!weight || max <= 0)
    return undefined;
  return `${(weight(item) / max) * 100}%`;
}
</script>

<template>
  <RuiCard no-padding>
    <template #custom-header>
      <div class="flex items-center gap-2 px-4 pt-4 pb-2">
        <span class="flex shrink-0 text-rui-text-secondary">
          <slot name="header-icon" />
        </span>
        <h3 class="text-base font-semibold text-rui-text">
          <slot name="header" />
        </h3>
      </div>
    </template>
    <ol class="flex flex-col px-2 pb-2">
      <li
        v-for="(item, index) in visibleItems"
        :key="index"
        class="relative flex items-center gap-3 h-11 px-2 text-sm"
        data-testid="wrapped-row"
      >
        <span
          v-if="barWidth(item)"
          class="absolute inset-y-1 left-0 rounded-rui-sm bg-rui-primary/6"
          :style="{ width: barWidth(item) }"
        />
        <span
          v-if="ranked"
          class="relative w-5 shrink-0 text-xs text-rui-text-secondary tabular-nums"
        >
          {{ index + 1 }}
        </span>
        <span class="relative flex min-w-0 grow items-center gap-2 text-rui-text">
          <slot
            name="label"
            v-bind="{ item, index }"
          >
            {{ 'label' in item ? item.label : item }}
          </slot>
        </span>
        <span class="relative flex shrink-0 items-baseline gap-1 font-medium tabular-nums text-rui-text">
          <slot
            name="value"
            v-bind="{ item, index }"
          >
            {{ 'value' in item ? item.value : item }}
          </slot>
        </span>
      </li>
    </ol>
    <div
      v-if="hasMore"
      class="px-2 pb-2 -mt-1"
    >
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        data-testid="wrapped-toggle"
        @click="showAll = !showAll"
      >
        {{ showAll ? t('wrapped.show_less') : t('wrapped.show_all', { count: items.length }) }}
      </RuiButton>
    </div>
  </RuiCard>
</template>
