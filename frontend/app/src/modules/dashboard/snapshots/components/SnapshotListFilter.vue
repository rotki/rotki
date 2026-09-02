<script lang="ts" setup>
import type { SnapshotListFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { toSnapshotListMatches, useSnapshotListFields } from '@/modules/dashboard/snapshots/composables/use-snapshot-list-fields';

const modelValue = defineModel<SnapshotListFilters>({ required: true });

const fields = useSnapshotListFields();
const pillLabels = usePillBarLabels();

/**
 * The page's `{ fromTimestamp, toTimestamp }` model, as the flat keyword map the pill bar speaks.
 * Bridging the two is why this component exists, the same way `KrakenDateFilter` does.
 */
const matches = toSnapshotListMatches(modelValue);
</script>

<template>
  <PillFilterBar
    v-model:matches="matches"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
