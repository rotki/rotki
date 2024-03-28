<script setup lang="ts">
import type { EvmUnDecodedTransactionsData } from '@/types/websocket-messages';

const props = defineProps<{ item: EvmUnDecodedTransactionsData; decoding: boolean }>();

const { t } = useI18n();

const isComplete = computed(() => props.item.total === props.item.processed);
</script>

<template>
  <div class="flex items-center gap-2">
    <AdaptiveWrapper>
      <EvmChainIcon
        :chain="item.evmChain"
        size="1.25rem"
      />
    </AdaptiveWrapper>
    <div class="flex flex-wrap text-body-2">
      <template v-if="isComplete">
        {{ t('transactions.events_decoding.decoding.done', { count: item.total }) }}
      </template>
      <template v-else-if="!decoding">
        {{ t('transactions.events_decoding.decoding.pending', { count: item.total }) }}
      </template>
      <template v-else>
        {{ t('transactions.events_decoding.decoding.processing', { count: item.processed, total: item.total }) }}
      </template>
    </div>
  </div>
</template>
