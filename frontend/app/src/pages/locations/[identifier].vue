<script setup lang="ts">
import { msg } from '@/message-key';
import LocationAssets from '@/modules/balances/LocationAssets.vue';
import LocationValueRow from '@/modules/balances/LocationValueRow.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import { useLocations } from '@/modules/core/common/use-locations';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    // label-only: gives the notes sidebar a title; not shown in the drawer or search.
    nav: { labelKey: msg.$t('navigation_menu.locations'), icon: 'lu-coins-exchange', searchable: false },
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
    <div
      v-if="location"
      class="flex items-center gap-4 min-h-13"
    >
      <LocationIcon
        :item="identifier"
        icon
        size="48px"
      />
      <span class="text-h5 font-semibold capitalize">
        {{ location.name }}
      </span>
    </div>
    <LocationValueRow
      :key="`value-${identifier}`"
      :identifier="identifier"
    />
    <LocationAssets
      :key="`assets-${identifier}`"
      :identifier="identifier"
    />
  </TablePageLayout>
</template>
