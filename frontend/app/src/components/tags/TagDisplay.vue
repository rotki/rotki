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
  <span
    v-if="tags"
    class="mt-2 flex-row d-flex align-center"
    :class="wrapperClass"
  >
    <span v-if="tags.length > 0">
      <TagIcon
        v-for="tag in tags"
        :key="tag"
        :small="small"
        class="mr-2 mb-1"
        :tag="availableTags[tag]"
      />
    </span>
  </span>
</template>
