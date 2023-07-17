<script setup lang="ts">
import { type HistoryEventsQueryData } from '@/types/websocket-messages';

defineProps<{ item: HistoryEventsQueryData }>();

const { getItemTranslationKey } = useEventsQueryStatus();
</script>

<template>
  <I18n
    :path="getItemTranslationKey(item)"
    tag="div"
    class="d-flex py-2 text-no-wrap flex-wrap"
  >
    <template #name>
      <div class="font-weight-bold px-2 text-no-wrap">
        <HashLink :text="item.name" no-link :show-icon="false" />
      </div>
    </template>
    <template #start>
      <div v-if="item.period" class="font-weight-bold px-1 text-no-wrap">
        <DateDisplay :timestamp="item.period[0]" />
      </div>
    </template>
    <template #end>
      <div v-if="item.period" class="font-weight-bold px-1 text-no-wrap">
        <DateDisplay :timestamp="item.period[1]" />
      </div>
    </template>
  </I18n>
</template>
