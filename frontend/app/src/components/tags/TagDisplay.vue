<script setup lang="ts">
withDefaults(
  defineProps<{
    tags?: string[];
    small?: boolean;
    wrapperClass?: string;
  }>(),
  {
    tags: () => [],
    small: false,
    wrapperClass: ''
  }
);

const { availableTags } = storeToRefs(useTagStore());
</script>

<template>
  <div
    v-if="tags && tags.length > 0"
    class="mt-2 flex-row flex items-center gap-2"
    :class="wrapperClass"
  >
    <TagIcon
      v-for="tag in tags"
      :key="tag"
      :small="small"
      :tag="availableTags[tag]"
    />
  </div>
</template>
