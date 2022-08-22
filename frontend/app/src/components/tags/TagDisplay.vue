<template>
  <span
    v-if="tags"
    class="mt-2 flex-row d-flex align-center"
    :class="wrapperClass"
  >
    <span v-if="tags.length > 0">
      <tag-icon
        v-for="tag in tags"
        :key="tag"
        :small="small"
        class="mr-2 mb-1"
        :tag="availableTags[tag]"
      />
    </span>
  </span>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import TagIcon from '@/components/tags/TagIcon.vue';
import { useTagStore } from '@/store/session/tags';

export default defineComponent({
  name: 'TagDisplay',
  components: {
    TagIcon
  },
  props: {
    tags: {
      required: false,
      type: Array as PropType<string[]>,
      default: () => []
    },
    small: { required: false, type: Boolean, default: false },
    wrapperClass: { required: false, type: String, default: '' }
  },
  setup() {
    const { availableTags } = storeToRefs(useTagStore());
    return {
      availableTags
    };
  }
});
</script>
