<script setup lang="ts">
const props = defineProps<{
  value: string;
  tooltip: string;
  size?: string;
}>();

const { value } = toRefs(props);
const { copy } = useClipboard({ source: value });
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top', offsetDistance: 0 }"
    open-delay="400"
  >
    <template #activator="{ on, attrs }">
      <RuiButton
        :size="size"
        variant="text"
        v-bind="attrs"
        icon
        @click="copy()"
        v-on="on"
      >
        <RuiIcon size="14" name="file-copy-line" />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </RuiTooltip>
</template>
