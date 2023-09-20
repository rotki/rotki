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
    class="flex py-2 text-no-wrap flex-wrap"
  >
    <template #status>
      {{ getLabel(item) }}
    </template>
    <template #address>
      <div class="font-bold px-2 text-no-wrap">
        <HashLink :text="item.address" :chain="getChain(item.evmChain)" />
      </div>
    </template>
    <template #start>
      <div class="font-bold px-1 text-no-wrap">
        <DateDisplay :timestamp="item.period[0]" />
      </div>
    </template>
    <template #end>
      <div class="font-bold px-1 text-no-wrap">
        <DateDisplay :timestamp="item.period[1]" />
      </div>
    </template>
  </i18n>
</template>
