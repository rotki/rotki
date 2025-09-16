<script setup lang="ts">
import type { Filters, Matcher } from '@/composables/filters/blockchain-account';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { SavedFilterLocation } from '@/types/filtering';

interface Props {
  visibleTags: string[];
  filters: Filters;
  matchers: Matcher[];
}

const visibleTagsModel = defineModel<string[]>('visibleTags', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

defineProps<Props>();
</script>

<template>
  <div class="flex items-center gap-2 flex-wrap">
    <TagFilter
      v-model="visibleTagsModel"
      class="w-[20rem] max-w-[30rem]"
      hide-details
    />
    <TableFilter
      v-model:matches="filtersModel"
      :matchers="matchers"
      class="max-w-[calc(100vw-11rem)] w-[25rem] lg:max-w-[30rem]"
      :location="SavedFilterLocation.BLOCKCHAIN_ACCOUNTS"
    />
  </div>
</template>
