<script setup lang="ts">
import type { EvmTransactionQueryData } from '@/types/websocket-messages';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useTransactionQueryStatus } from '@/composables/history/events/query-status/tx-query-status';
import HashLink from '@/modules/common/links/HashLink.vue';

defineProps<{ item: EvmTransactionQueryData }>();

const { getItemTranslationKey, getLabel } = useTransactionQueryStatus();
</script>

<template>
  <i18n-t
    :keypath="getItemTranslationKey(item)"
    tag="div"
    class="flex items-center py-2 text-no-wrap flex-wrap text-body-2 gap-x-2 gap-y-1"
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
          :location="item.evmChain"
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
