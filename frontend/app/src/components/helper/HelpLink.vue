<script setup lang="ts">
import { useLinks } from '@/composables/links';

const props = withDefaults(
  defineProps<{
    url: string;
    tooltip: string;
    small?: boolean;
  }>(),
  {
    small: false,
  },
);

const { url } = toRefs(props);
const { href, onLinkClick } = useLinks(url);
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        type="button"
        variant="text"
        icon
        :size="small ? 'sm' : undefined"
        :href="href"
        target="_blank"
        tag="a"
        @click="onLinkClick()"
      >
        <RuiIcon
          :size="small ? 20 : 24"
          name="lu-circle-question-mark"
        />
      </RuiButton>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>
