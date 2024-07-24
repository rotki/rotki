<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

defineOptions({
  name: 'LocationBreakdown',
});

const props = defineProps<{
  identifier: string;
}>();

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.LOCATIONS,
  },
  props: true,
});

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
      <DepositsWithdrawalsContent :location-overview="identifier" />
    </div>
  </TablePageLayout>
</template>
