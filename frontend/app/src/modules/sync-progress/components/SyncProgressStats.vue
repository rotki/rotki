<script setup lang="ts">
interface StatGroup {
  hasData: boolean;
  isComplete: boolean;
  hasCancelled?: boolean;
  completed: number;
  total: number;
}

defineProps<{
  chains: StatGroup;
  locations: StatGroup;
  decoding: StatGroup;
  protocolCache?: StatGroup;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-3 text-xs text-rui-text-secondary">
    <span
      v-if="chains.hasData"
      :class="{
        'text-rui-warning': chains.isComplete && chains.hasCancelled,
        'text-rui-success': chains.isComplete && !chains.hasCancelled,
      }"
    >
      <span class="tabular-nums">{{ chains.completed }}/{{ chains.total }}</span>
      {{ t('sync_progress.chains_label', chains.total) }}
    </span>

    <span
      v-if="locations.hasData"
      :class="{
        'text-rui-warning': locations.isComplete && locations.hasCancelled,
        'text-rui-success': locations.isComplete && !locations.hasCancelled,
      }"
    >
      <span class="tabular-nums">{{ locations.completed }}/{{ locations.total }}</span>
      {{ t('sync_progress.locations_label', locations.total) }}
    </span>

    <span
      v-if="decoding.hasData"
      :class="{
        'text-rui-warning': decoding.isComplete && decoding.hasCancelled,
        'text-rui-success': decoding.isComplete && !decoding.hasCancelled,
      }"
    >
      <span class="tabular-nums">{{ decoding.completed }}/{{ decoding.total }}</span>
      {{ t('sync_progress.decoding_label', decoding.total) }}
    </span>

    <span
      v-if="protocolCache?.hasData"
      :class="{
        'text-rui-warning': protocolCache.isComplete && protocolCache.hasCancelled,
        'text-rui-success': protocolCache.isComplete && !protocolCache.hasCancelled,
      }"
    >
      <span class="tabular-nums">{{ protocolCache.completed }}/{{ protocolCache.total }}</span>
      {{ t('sync_progress.protocol_cache_label', protocolCache.total) }}
    </span>
  </div>
</template>
