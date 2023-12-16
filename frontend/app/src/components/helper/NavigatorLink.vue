<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';

const props = withDefaults(
  defineProps<{
    tag?: string;
    enabled?: boolean;
    to: RouteLocationRaw;
  }>(),
  {
    tag: 'span',
    enabled: true,
  },
);

const { enabled, to } = toRefs(props);
const router = useRouter();

async function navigate() {
  if (get(enabled))
    await router.push(get(to));
}

const attrs = useAttrs();
</script>

<template>
  <Component
    :is="tag"
    :class="{ 'cursor-pointer': enabled }"
    v-bind="attrs"
    @click="navigate()"
  >
    <slot />
  </Component>
</template>
