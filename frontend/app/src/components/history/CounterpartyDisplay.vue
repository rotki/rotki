<script setup lang="ts">
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';

const props = defineProps<{
  counterparty: string;
}>();

const { counterparty } = toRefs(props);

const { getCounterpartyData } = useHistoryEventCounterpartyMappings();

const data = getCounterpartyData(counterparty);
const imagePath = '/assets/images/protocols/';
</script>

<template>
  <div class="flex items-center gap-3">
    <div class="icon-bg">
      <RuiIcon
        v-if="data.icon"
        :name="data.icon"
        :color="data.color || 'secondary'"
        size="20px"
      />

      <AppImage
        v-else-if="data.image"
        :src="`${imagePath}${data.image}`"
        contain
        size="20px"
      />
    </div>
    <div class="uppercase text-sm">
      {{ data.label }}
    </div>
  </div>
</template>
