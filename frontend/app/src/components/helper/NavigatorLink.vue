<template>
  <component
    :is="component"
    :class="{ [$style.link]: enabled }"
    v-bind="$attrs"
    @click="navigate"
  >
    <slot />
  </component>
</template>
<script lang="ts">
import { defineComponent, PropType, toRefs } from '@vue/composition-api';
import { RawLocation } from 'vue-router';
import { useRouter } from '@/composables/common';

export default defineComponent({
  props: {
    component: { required: false, type: String, default: 'span' },
    enabled: { required: false, type: Boolean, default: true },
    to: { required: true, type: Object as PropType<RawLocation> }
  },
  setup(props) {
    const { enabled, to } = toRefs(props);

    const router = useRouter();

    const navigate = () => {
      if (enabled) {
        router.push(to.value);
      }
    };

    return {
      navigate
    };
  }
});
</script>
<style module lang="scss">
.link {
  cursor: pointer;
}
</style>
