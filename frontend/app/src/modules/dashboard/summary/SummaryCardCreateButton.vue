<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';

const { to } = defineProps<{ to?: RouteLocationRaw }>();

const router = useRouter();

function navigate() {
  if (to) {
    router.push(to);
  }
}
</script>

<template>
  <div class="px-6 w-full">
    <RuiButton
      variant="text"
      color="primary"
      tag="a"
      class="py-2 w-full"
      @click="navigate()"
    >
      <div class="flex flex-col gap-2 items-center">
        <RuiIcon name="lu-circle-plus" />
        <span>
          <slot />
        </span>
      </div>
    </RuiButton>
  </div>
</template>
