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
import { computed, defineComponent } from '@vue/composition-api';
import TagIcon from '@/components/tags/TagIcon.vue';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'TagDisplay',
  components: {
    TagIcon
  },
  props: {
    tags: { required: false, type: Array, default: () => [] },
    small: { required: false, type: Boolean, default: false },
    wrapperClass: { required: false, type: String, default: '' }
  },
  setup() {
    const store = useStore();
    const availableTags = computed(
      () => store.getters['session/availableTags']
    );

    return {
      availableTags
    };
  }
});
</script>
