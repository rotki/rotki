<script setup lang="ts">
import { toRefs } from 'vue';

const props = withDefaults(
  defineProps<{
    url: string;
    tooltip: string;
    small?: boolean;
  }>(),
  {
    small: false
  }
);

const { url } = toRefs(props);
const { href, onLinkClick } = useLinks(url);
</script>

<template>
  <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
    <template #activator>
      <RuiButton
        type="button"
        variant="text"
        icon
        :size="small ? 'sm' : 'md'"
        :href="href"
        target="_blank"
        tag="a"
        @click="onLinkClick()"
      >
        <RuiIcon :size="small ? 20 : 24" name="question-line" />
      </RuiButton>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>
