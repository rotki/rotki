<script setup lang="ts">
import { useSharedClipboard } from '@/modules/core/common/use-clipboard';

const { value, tooltip, size } = defineProps<{
  value: string;
  tooltip: string;
  size?: 'sm' | 'lg';
}>();

const { copy: copyClipboard } = useSharedClipboard();

async function copy(): Promise<void> {
  await copyClipboard(value);
}
</script>

<template>
  <RuiTooltip
    :options="{ offset: 0, placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        :size="size"
        variant="text"
        icon
        @click="copy()"
      >
        <RuiIcon
          size="16"
          name="lu-copy"
        />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </RuiTooltip>
</template>
