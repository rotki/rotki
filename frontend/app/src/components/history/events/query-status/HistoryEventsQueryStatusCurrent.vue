<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

const props = withDefaults(
  defineProps<{
    locations?: Blockchain[];
  }>(),
  {
    locations: () => []
  }
);

const { locations } = toRefs(props);

const { t } = useI18n();

const { isAllFinished } = toRefs(useEventsQueryStatusStore());
const { queryingLength, length } = useEventsQueryStatus(locations);
</script>

<template>
  <div>
    <div v-if="isAllFinished">
      {{ t('transactions.query_status_events.done_group', { length }) }}
    </div>
    <div v-else>
      {{
        t('transactions.query_status_events.group', {
          length: queryingLength
        })
      }}
    </div>
  </div>
</template>
