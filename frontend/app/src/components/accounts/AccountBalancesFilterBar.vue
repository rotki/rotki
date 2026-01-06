<script setup lang="ts">
import TagFilter from '@/components/inputs/TagFilter.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { type MatchedKeywordWithBehaviour, SavedFilterLocation, type SearchMatcher } from '@/types/filtering';

const visibleTags = defineModel<string[]>('visibleTags', { required: true });
const filters = defineModel<MatchedKeywordWithBehaviour<any>>('filters', { required: true });

defineProps<{
  matchers: SearchMatcher<any, any>[];
}>();
</script>

<template>
  <div class="flex items-center gap-2 flex-wrap">
    <TagFilter
      v-model="visibleTags"
      class="w-[20rem] max-w-[30rem]"
      hide-details
    />
    <TableFilter
      v-model:matches="filters"
      :matchers="matchers"
      class="max-w-[calc(100vw-11rem)] w-[25rem] lg:max-w-[30rem]"
      :location="SavedFilterLocation.BLOCKCHAIN_ACCOUNTS"
    />
  </div>
</template>
