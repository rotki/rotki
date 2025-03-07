<script setup lang="ts">
import type { EvmTransactionQueryData } from '@/types/websocket-messages';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import TransactionQueryStatusLine from '@/components/history/events/tx/query-status/TransactionQueryStatusLine.vue';

defineProps<{ item: EvmTransactionQueryData }>();
</script>

<template>
  <div class="flex items-center">
    <AdaptiveWrapper>
      <EvmChainIcon
        :chain="item.evmChain"
        size="1.25rem"
      />
    </AdaptiveWrapper>
    <TransactionQueryStatusLine
      :item="item"
      class="ms-2"
    />

    <RuiTooltip
      class="ml-2 cursor-pointer"
      :open-delay="400"
      tooltip-class="max-w-[12rem]"
    >
      <template #activator>
        <RuiIcon
          class="text-rui-text-secondary"
          name="lu-circle-help"
          size="18"
        />
      </template>

      <i18n-t
        :keypath="
          item.period[0] === 0
            ? 'transactions.query_status.latest_period_end_date'
            : 'transactions.query_status.latest_period_date_range'
        "
        tag="span"
      >
        <template #start>
          <DateDisplay :timestamp="item.period[0]" />
        </template>
        <template #end>
          <DateDisplay :timestamp="item.period[1]" />
        </template>
      </i18n-t>
    </RuiTooltip>
  </div>
</template>
