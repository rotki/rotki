<script setup lang="ts">
import type { TxQueryStatusData } from '@/store/history/query-status/tx-query-status';
import DateDisplay from '@/components/display/DateDisplay.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import TransactionQueryStatusLine from '@/components/history/events/tx/query-status/TransactionQueryStatusLine.vue';

defineProps<{ item: TxQueryStatusData }>();
</script>

<template>
  <div class="flex items-center">
    <ChainIcon
      :chain="item.chain"
      size="1.5rem"
    />
    <TransactionQueryStatusLine
      :item="item"
      class="ms-2"
    />

    <RuiTooltip
      v-if="item.subtype !== 'bitcoin' && item.period"
      class="ml-2 cursor-pointer"
      :open-delay="400"
      tooltip-class="max-w-[12rem]"
    >
      <template #activator>
        <RuiIcon
          class="text-rui-text-secondary"
          name="lu-circle-question-mark"
          size="18"
        />
      </template>

      <i18n-t
        scope="global"
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
