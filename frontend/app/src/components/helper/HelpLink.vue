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
  <VTooltip open-delay="400" top>
    <template #activator="{ attrs, on }">
      <VBtn
        icon
        :small="small"
        v-bind="attrs"
        :href="href"
        target="_blank"
        v-on="on"
        @click="onLinkClick()"
      >
        <VIcon :small="small">mdi-help-circle</VIcon>
      </VBtn>
    </template>
    {{ tooltip }}
  </VTooltip>
</template>
