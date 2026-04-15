<script setup lang="ts">
import LocationIcon from '@/components/history/LocationIcon.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import LocationAssets from '@/components/locations/LocationAssets.vue';
import LocationValueRow from '@/components/locations/LocationValueRow.vue';
import { useLocations } from '@/composables/locations';
import { NoteLocation } from '@/modules/common/notes';

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

const { identifier } = defineProps<{
  identifier: string;
}>();

const { useLocationData } = useLocations();
const location = useLocationData(() => identifier);
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
    </div>
  </TablePageLayout>
</template>
