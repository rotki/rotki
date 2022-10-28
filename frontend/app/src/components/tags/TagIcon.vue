<template>
  <v-chip
    class="tag font-weight-medium"
    label
    :small="small"
    :color="`#${tag.backgroundColor}`"
    :text-color="`#${tag.foregroundColor}`"
  >
    <v-img
      v-if="tag.icon"
      class="mr-2"
      :width="20"
      :height="20"
      :src="tag.icon"
    />
    <span>{{ tag.name }}</span>
  </v-chip>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { Tag } from '@/types/user';

defineProps({
  tag: { required: true, type: Object as PropType<Tag> },
  small: { required: false, type: Boolean, default: false }
});
</script>
