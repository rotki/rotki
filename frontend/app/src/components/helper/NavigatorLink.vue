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
<script setup lang="ts">
import { PropType } from 'vue';
import { RawLocation } from 'vue-router';

const props = defineProps({
  component: { required: false, type: String, default: 'span' },
  enabled: { required: false, type: Boolean, default: true },
  to: { required: true, type: Object as PropType<RawLocation> }
});

const { enabled, to } = toRefs(props);
const router = useRouter();

const navigate = async () => {
  if (enabled) {
    await router.push(to.value);
  }
};
</script>
<style module lang="scss">
.link {
  cursor: pointer;
}
</style>
