<script setup lang="ts">
import { useLocations } from '@/modules/core/common/use-locations';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';

const { location } = defineProps<{
  location: string;
}>();

const { useLocationData } = useLocations();

const data = useLocationData(() => location);
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
    :open-delay="400"
    :disabled="!data"
  >
    <template #activator>
      <LocationDisplay
        icon
        size="20px"
        :identifier="location"
        :aria-label="data?.name"
        data-testid="pnl-event-location"
      />
    </template>
    {{ data?.name }}
  </RuiTooltip>
</template>
