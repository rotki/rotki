<script setup lang="ts">
import type { TxQueryStatusData } from '@/store/history/query-status/tx-query-status';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useTransactionQueryStatus } from '@/composables/history/events/query-status/tx-query-status';
import HashLink from '@/modules/common/links/HashLink.vue';

defineProps<{ item: TxQueryStatusData }>();

const { getItemTranslationKey, getLabel } = useTransactionQueryStatus();
</script>

<template>
  <i18n-t
    scope="global"
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
          :location="item.chain"
        />
      </div>
    </template>
    <template
      v-if="item.subtype !== 'bitcoin' && item.period"
      #start
    >
      <div class="font-bold text-no-wrap">
        <DateDisplay :timestamp="item.period[0]" />
      </div>
    </template>
    <template
      v-if="item.subtype !== 'bitcoin' && item.period"
      #end
    >
      <div class="font-bold text-no-wrap">
        <DateDisplay :timestamp="item.period[1]" />
      </div>
    </template>
  </i18n-t>
</template>
