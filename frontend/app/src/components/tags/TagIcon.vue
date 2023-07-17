<script setup lang="ts">
import { type PropType } from 'vue';
import { type Tag } from '@/types/tags';

defineProps({
  tag: { required: true, type: Object as PropType<Tag> },
  small: { required: false, type: Boolean, default: false }
});
</script>

<template>
  <VChip
    class="tag font-weight-medium"
    label
    :small="small"
    :color="`#${tag.backgroundColor}`"
    :text-color="`#${tag.foregroundColor}`"
  >
    <VImg
      v-if="tag.icon"
      class="mr-2"
      :width="20"
      :height="20"
      :src="tag.icon"
    />
    <span>{{ tag.name }}</span>
  </VChip>
</template>
