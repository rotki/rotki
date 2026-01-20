<script setup lang="ts">
import { useSyncProgress } from '../composables/use-sync-progress';
import ChainProgressList from './ChainProgressList.vue';
import DecodingProgressList from './DecodingProgressList.vue';
import LocationProgressList from './LocationProgressList.vue';
import ProtocolCacheProgressList from './ProtocolCacheProgressList.vue';

const { t } = useI18n({ useScope: 'global' });

const { chains, locations, decoding, protocolCache, completedChains, totalChains, completedLocations, totalLocations } = useSyncProgress();

const hasChains = computed<boolean>(() => get(chains).length > 0);
const hasLocations = computed<boolean>(() => get(locations).length > 0);
const hasDecoding = computed<boolean>(() => get(decoding).length > 0);
const hasProtocolCache = computed<boolean>(() => get(protocolCache).length > 0);

const chainsComplete = computed<boolean>(() => get(completedChains) === get(totalChains) && get(totalChains) > 0);
const locationsComplete = computed<boolean>(() => get(completedLocations) === get(totalLocations) && get(totalLocations) > 0);

const decodingCompleted = computed<number>(() => get(decoding).filter(d => d.processed >= d.total).length);
const decodingTotal = computed<number>(() => get(decoding).length);
const decodingComplete = computed<boolean>(() => get(decodingCompleted) === get(decodingTotal) && get(decodingTotal) > 0);

const protocolCacheCompleted = computed<number>(() => get(protocolCache).filter(p => p.processed >= p.total).length);
const protocolCacheTotal = computed<number>(() => get(protocolCache).length);
const protocolCacheComplete = computed<boolean>(() => get(protocolCacheCompleted) === get(protocolCacheTotal) && get(protocolCacheTotal) > 0);
</script>

<template>
  <div class="px-3 pb-4 space-y-5">
    <div
      v-if="hasChains"
      class="pt-4"
    >
      <div class="flex items-center gap-2 mb-2">
        <span class="text-xs font-medium text-rui-text-secondary">
          {{ t('sync_progress.transactions') }}
        </span>
        <span
          class="text-xs tabular-nums"
          :class="chainsComplete ? 'text-rui-success' : 'text-rui-text-disabled'"
        >
          {{ completedChains }}/{{ totalChains }}
        </span>
        <RuiIcon
          v-if="chainsComplete"
          name="lu-check"
          class="text-rui-success"
          size="12"
        />
      </div>
      <ChainProgressList :chains="chains" />
    </div>

    <div
      v-if="hasLocations"
      :class="{ 'pt-4': !hasChains }"
    >
      <div class="flex items-center gap-2 mb-2">
        <span class="text-xs font-medium text-rui-text-secondary">
          {{ t('sync_progress.events') }}
        </span>
        <span
          class="text-xs tabular-nums"
          :class="locationsComplete ? 'text-rui-success' : 'text-rui-text-disabled'"
        >
          {{ completedLocations }}/{{ totalLocations }}
        </span>
        <RuiIcon
          v-if="locationsComplete"
          name="lu-check"
          class="text-rui-success"
          size="12"
        />
      </div>
      <LocationProgressList :locations="locations" />
    </div>

    <div
      v-if="hasDecoding"
      :class="{ 'pt-4': !hasChains && !hasLocations }"
    >
      <div class="flex items-center gap-2 mb-2">
        <span class="text-xs font-medium text-rui-text-secondary">
          {{ t('sync_progress.decoding') }}
        </span>
        <span
          class="text-xs tabular-nums"
          :class="decodingComplete ? 'text-rui-success' : 'text-rui-text-disabled'"
        >
          {{ decodingCompleted }}/{{ decodingTotal }}
        </span>
        <RuiIcon
          v-if="decodingComplete"
          name="lu-check"
          class="text-rui-success"
          size="12"
        />
      </div>
      <DecodingProgressList :decoding="decoding" />
    </div>

    <div
      v-if="hasProtocolCache"
      :class="{ 'pt-4': !hasChains && !hasLocations && !hasDecoding }"
    >
      <div class="flex items-center gap-2 mb-2">
        <span class="text-xs font-medium text-rui-text-secondary">
          {{ t('sync_progress.protocol_cache') }}
        </span>
        <span
          class="text-xs tabular-nums"
          :class="protocolCacheComplete ? 'text-rui-success' : 'text-rui-text-disabled'"
        >
          {{ protocolCacheCompleted }}/{{ protocolCacheTotal }}
        </span>
        <RuiIcon
          v-if="protocolCacheComplete"
          name="lu-check"
          class="text-rui-success"
          size="12"
        />
      </div>
      <ProtocolCacheProgressList :protocol-cache="protocolCache" />
    </div>
  </div>
</template>
