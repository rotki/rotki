<script setup lang="ts">
const props = defineProps<{
  value: string;
  tooltip: string;
  size?: 'sm' | 'lg';
}>();

const { value } = toRefs(props);
const { copy } = useClipboard({ source: value });
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top', offsetDistance: 0 }"
    open-delay="400"
  >
    <template #activator>
      <RuiButton :size="size" variant="text" icon @click="copy()">
        <RuiIcon size="16" name="file-copy-line" />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </RuiTooltip>
</template>
