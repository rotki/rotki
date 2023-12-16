<script setup lang="ts">
import type { EvmTransactionQueryData } from '@/types/websocket-messages';

defineProps<{ item: EvmTransactionQueryData }>();

const { getLabel, getItemTranslationKey } = useTransactionQueryStatus();
const { getChain } = useSupportedChains();
</script>

<template>
  <i18n-t
    :keypath="getItemTranslationKey(item)"
    tag="div"
    class="flex py-2 text-no-wrap flex-wrap text-body-2 gap-2"
  >
    <template #status>
      <span>
        {{ getLabel(item) }}
      </span>
    </template>
    <template #address>
      <div class="font-bold text-no-wrap">
        <HashLink
          :text="item.address"
          :chain="getChain(item.evmChain)"
        />
      </div>
    </template>
    <template #start>
      <div class="font-bold text-no-wrap">
        <DateDisplay :timestamp="item.period[0]" />
      </div>
    </template>
    <template #end>
      <div class="font-bold text-no-wrap">
        <DateDisplay :timestamp="item.period[1]" />
      </div>
    </template>
  </i18n-t>
</template>
