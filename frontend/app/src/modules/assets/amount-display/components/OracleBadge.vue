<script setup lang="ts">
defineProps<{
  oracle: string;
}>();
</script>

<template>
  <RuiChip
    color="warning"
    content-class="!text-[10px]"
    class="font-bold leading-3 uppercase !p-0.5 mb-0.5 mt-0.5"
    size="sm"
  >
    <div class="flex gap-1">
      <RuiIcon
        name="lu-info"
        size="12"
      />
      {{ oracle }}
    </div>
  </RuiChip>
</template>
