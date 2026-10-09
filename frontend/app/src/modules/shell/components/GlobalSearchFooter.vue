<script setup lang="ts">
const { assetSearchError } = defineProps<{
  /** Why the asset search failed, if it did; pages and settings still search without it. */
  assetSearchError?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

/** The keys the palette answers to, drawn as keycaps beside what they do. */
const hints = computed<{ keys: string[]; label: string }[]>(() => [
  { keys: ['↑', '↓'], label: t('global_search.hints.navigate') },
  { keys: ['↵'], label: t('global_search.hints.open') },
  { keys: ['esc'], label: t('global_search.hints.close') },
]);
</script>

<template>
  <div class="border-t border-rui-divider px-3 py-2 flex items-center gap-4 text-xs text-rui-text-secondary">
    <!-- a note rather than an alarm: everything but assets still searches -->
    <RuiTooltip
      v-if="assetSearchError"
      :open-delay="300"
      class="me-auto min-w-0"
    >
      <template #activator>
        <span
          class="flex items-center gap-1.5"
          role="status"
          aria-live="polite"
          data-testid="global-search-asset-error"
        >
          <RuiIcon
            name="lu-circle-alert"
            size="14"
            class="shrink-0 text-rui-warning"
          />
          <span class="truncate">{{ t('global_search.asset_search_unavailable') }}</span>
        </span>
      </template>
      {{ t('asset_search.error.message', { message: assetSearchError }) }}
    </RuiTooltip>
    <div
      class="flex items-center gap-4 shrink-0"
      :class="{ 'ms-auto': !assetSearchError }"
      aria-hidden="true"
      data-testid="global-search-hints"
    >
      <span
        v-for="hint in hints"
        :key="hint.label"
        class="flex items-center gap-1"
      >
        <kbd
          v-for="key in hint.keys"
          :key="key"
          class="inline-flex items-center justify-center min-w-5 h-5 px-1 rounded-rui-sm border border-rui-divider bg-rui-surface font-sans text-[0.6875rem]"
        >
          {{ key }}
        </kbd>
        {{ hint.label }}
      </span>
    </div>
  </div>
</template>
