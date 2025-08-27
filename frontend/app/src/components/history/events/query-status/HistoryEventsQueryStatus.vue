<script lang="ts" setup>
import type { HistoryEventsQueryData } from '@/modules/messaging/types';
import HistoryEventsQueryStatusCurrent from './HistoryEventsQueryStatusCurrent.vue';
import HistoryEventsQueryStatusDetails from './HistoryEventsQueryStatusDetails.vue';

interface HistoryEventsQueryStatusProps {
  locations?: string[];
  events?: HistoryEventsQueryData[];
}

const props = withDefaults(defineProps<HistoryEventsQueryStatusProps>(), {
  events: () => [],
  locations: () => [],
});

const { events } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const itemHeight = 40;
const wrapperComponentStyle = {
  height: `${5 * itemHeight}px`,
};

const itemStyle = {
  height: `${get(itemHeight)}px`,
};

const { containerProps, list, wrapperProps } = useVirtualList(events, {
  itemHeight: get(itemHeight),
});
</script>

<template>
  <div>
    <h6 class="text-body-1 font-medium">
      {{ t('transactions.query_status_events.title') }}
    </h6>

    <HistoryEventsQueryStatusCurrent
      :locations="locations"
      class="text-subtitle-2 text-rui-text-secondary mt-2"
    />

    <div
      v-if="events.length > 0"
      v-bind="containerProps"
      :class="$style['scroll-container']"
      :style="wrapperComponentStyle"
    >
      <div v-bind="wrapperProps">
        <HistoryEventsQueryStatusDetails
          v-for="item in list"
          :key="item.index"
          :item="item.data"
          :style="itemStyle"
          class="py-1"
        />
      </div>
    </div>
  </div>
</template>

<style module lang="scss">
.scroll-container {
  &::-webkit-scrollbar-thumb {
    min-height: 30px;
  }
}
</style>
