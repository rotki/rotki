<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';

const props = defineProps<{ to: RouteLocationRaw }>();

const router = useRouter();

const href = computed(() => router.resolve(props.to).href);
</script>

<template>
  <div class="px-6">
    <RuiButton
      variant="text"
      color="primary"
      :href="href"
      tag="a"
      class="py-2 w-full"
    >
      <div class="flex flex-col gap-2 items-center">
        <RuiIcon name="add-circle-line" />
        <span>
          <slot />
        </span>
      </div>
    </RuiButton>
  </div>
</template>
