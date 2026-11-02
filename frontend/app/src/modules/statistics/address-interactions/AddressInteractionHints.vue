<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-0.5 text-xs text-rui-text-secondary">
    <span>{{ t('address_interactions.canvas_hint') }}</span>
    <span
      class="inline-flex items-center gap-1.5"
      data-testid="interaction-decoded-hint"
    >
      <RuiIcon
        name="lu-info"
        size="14"
        class="shrink-0"
      />
      {{ t('address_interactions.decoded_events_hint') }}
    </span>
  </div>
</template>
