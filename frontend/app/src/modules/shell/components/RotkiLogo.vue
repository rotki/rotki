<script setup lang="ts">
import type { LogoProps } from '@rotki/ui-library';

defineOptions({
  inheritAttrs: false,
});

const { text = false, uniqueKey, size } = defineProps<{
  uniqueKey?: LogoProps['uniqueKey'];
  text?: LogoProps['text'];
  size?: LogoProps['size'];
}>();
</script>

<template>
  <RuiLogo
    v-bind="$attrs"
    logo="app"
    :text="text"
    :size="size"
    :unique-key="uniqueKey"
  />
</template>
