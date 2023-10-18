<script setup lang="ts">
defineProps<{ to: string }>();
</script>

<template>
  <div class="px-6">
    <RuiButton
      variant="text"
      color="primary"
      :href="to"
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
