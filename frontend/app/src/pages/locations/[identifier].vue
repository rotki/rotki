<script setup lang="ts">
import LocationIcon from '@/components/history/LocationIcon.vue';
import ClosedTrades from '@/components/history/trades/ClosedTrades.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import LocationAssets from '@/components/locations/LocationAssets.vue';
import LocationValueRow from '@/components/locations/LocationValueRow.vue';
import { useLocations } from '@/composables/locations';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.LOCATIONS,
  },
  props: true,
});

defineOptions({
  name: 'LocationBreakdown',
});

const props = defineProps<{
  identifier: string;
}>();

const { identifier } = toRefs(props);
const { locationData } = useLocations();
const location = locationData(identifier);
</script>

<template>
  <TablePageLayout
    class="p-4"
    hide-header
  >
    <div class="flex flex-col gap-4 w-full">
      <div
        v-if="location"
        class="flex flex-row items-center mb-4 gap-2"
      >
        <LocationIcon
          :item="identifier"
          icon
          size="48px"
        />
        <span class="text-h5 font-medium">
          {{ location.name }}
        </span>
      </div>
      <LocationValueRow :identifier="identifier" />
      <LocationAssets :identifier="identifier" />
      <ClosedTrades :location-overview="identifier" />
    </div>
  </TablePageLayout>
</template>
