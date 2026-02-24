<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';

defineOptions({
  inheritAttrs: false,
});

const { enabled = true, tag = 'span', to } = defineProps<{
  tag?: string;
  enabled?: boolean;
  to: RouteLocationRaw | undefined;
}>();

const router = useRouter();

async function navigate(): Promise<void> {
  if (enabled && to !== undefined)
    await router.push(to);
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
