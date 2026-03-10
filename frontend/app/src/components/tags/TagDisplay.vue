<script setup lang="ts">
import TagIcon from '@/components/tags/TagIcon.vue';
import { useSessionMetadataStore } from '@/store/session/metadata';

const { tags = [], small = false, wrapperClass = '' } = defineProps<{
  tags?: string[];
  small?: boolean;
  wrapperClass?: string;
}>();

const { allTags } = storeToRefs(useSessionMetadataStore());
</script>

<template>
  <div
    v-if="tags && tags.length > 0"
    class="mt-2 flex flex-wrap items-center gap-1"
    :class="wrapperClass"
  >
    <TagIcon
      v-for="tag in tags"
      :key="tag"
      :small="small"
      :tag="allTags[tag]"
    />
  </div>
</template>
