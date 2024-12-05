<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    tag?: string;
    enabled?: boolean;
    to: RouteLocationRaw | undefined;
  }>(),
  {
    enabled: true,
    tag: 'span',
  },
);

const { enabled, to } = toRefs(props);
const router = useRouter();

async function navigate() {
  if (get(enabled) && isDefined(to))
    await router.push(get(to));
}
</script>

<template>
  <Component
    :is="tag"
    :class="{ 'cursor-pointer': enabled }"
    v-bind="$attrs"
    @click="navigate()"
  >
    <slot />
  </Component>
</template>
