<script setup lang="ts">
import { type PropType } from 'vue';

defineProps({
  tags: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  small: { required: false, type: Boolean, default: false },
  wrapperClass: { required: false, type: String, default: '' }
});

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
