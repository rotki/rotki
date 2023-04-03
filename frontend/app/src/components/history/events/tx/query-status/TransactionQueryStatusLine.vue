<script setup lang="ts">
import { type EvmTransactionQueryData } from '@/types/websocket-messages';

defineProps<{ item: EvmTransactionQueryData }>();

const { getLabel, getItemTranslationKey } = useTransactionQueryStatus();
const { getChain } = useSupportedChains();
</script>

<template>
  <i18n
    :path="getItemTranslationKey(item)"
    tag="div"
    class="d-flex py-2 text-no-wrap flex-wrap"
  >
    <template #status>
      {{ getLabel(item) }}
    </template>
    <template #address>
      <div class="font-weight-bold px-2 text-no-wrap">
        <hash-link :text="item.address" :chain="getChain(item.evmChain)" />
      </div>
    </template>
    <template #start>
      <div class="font-weight-bold px-1 text-no-wrap">
        <date-display :timestamp="item.period[0]" />
      </div>
    </template>
    <template #end>
      <div class="font-weight-bold px-1 text-no-wrap">
        <date-display :timestamp="item.period[1]" />
      </div>
    </template>
  </i18n>
</template>
