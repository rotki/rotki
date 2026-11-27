<script setup lang="ts">
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/history/data-issues/data-issue-filter-keys';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';

const filters = defineModel<Filters>({ required: true });

const { fields } = defineProps<{
  fields: FieldDef[];
}>();

const pillLabels = usePillBarLabels();
</script>

<template>
  <PillFilterBar
    v-model:matches="filters"
    class="flex-1 min-w-64"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
