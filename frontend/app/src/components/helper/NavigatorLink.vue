<script setup lang="ts">
import { type RawLocation } from 'vue-router';

const props = withDefaults(
  defineProps<{
    tag?: string;
    enabled?: boolean;
    to: RawLocation;
  }>(),
  {
    tag: 'span',
    enabled: true
  }
);

const { enabled, to } = toRefs(props);
const router = useRouter();

const navigate = async () => {
  if (enabled) {
    await router.push(to.value);
  }
};

const attrs = useAttrs();
</script>

<template>
  <component
    :is="tag"
    :class="{ 'cursor-pointer': enabled }"
    v-bind="attrs"
    @click="navigate()"
  >
    <slot />
  </component>
</template>
