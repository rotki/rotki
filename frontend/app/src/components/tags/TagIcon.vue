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

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { Tag } from '@/types/user';

export default defineComponent({
  name: 'TagIcon',
  props: {
    tag: { required: true, type: Object as PropType<Tag> },
    small: { required: false, type: Boolean, default: false }
  }
});
</script>
