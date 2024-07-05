<script setup lang="ts">
import type { ProtocolCacheUpdatesData } from '@/types/websocket-messages';

const props = defineProps<{ item: ProtocolCacheUpdatesData }>();

const { t } = useI18n();

const remaining = computed<number>(() => props.item.total - props.item.processed);

const isComplete = computed<boolean>(() => get(remaining) === 0);
</script>

<template>
  <div class="flex items-center gap-2">
    <AdaptiveWrapper>
      <EvmChainIcon
        :chain="item.chain"
        size="1.25rem"
      />
    </AdaptiveWrapper>
    <div class="flex flex-wrap text-body-2">
      <template v-if="isComplete">
        {{ t('transactions.events_decoding.decoding.done', { count: item.total }) }}
      </template>
      <template v-else>
        {{ t('transactions.events_decoding.decoding.processing', { count: item.processed, total: item.total }) }}
      </template>
    </div>
  </div>
</template>
