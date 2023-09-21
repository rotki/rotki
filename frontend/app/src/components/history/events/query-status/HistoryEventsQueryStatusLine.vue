<script setup lang="ts">
import { type HistoryEventsQueryData } from '@/types/websocket-messages';

defineProps<{ item: HistoryEventsQueryData }>();

const { getItemTranslationKey } = useEventsQueryStatus();
</script>

<template>
  <i18n
    :path="getItemTranslationKey(item)"
    tag="div"
    class="flex py-2 text-no-wrap flex-wrap"
  >
    <template #name>
      <div class="font-bold px-2 text-no-wrap">
        <HashLink
          :text="item.name"
          no-link
          :show-icon="false"
          disable-scramble
        />
      </div>
    </template>
    <template #start>
      <div v-if="item.period" class="font-bold px-1 text-no-wrap">
        <DateDisplay :timestamp="item.period[0]" />
      </div>
    </template>
    <template #end>
      <div v-if="item.period" class="font-bold px-1 text-no-wrap">
        <DateDisplay :timestamp="item.period[1]" />
      </div>
    </template>
  </i18n>
</template>
