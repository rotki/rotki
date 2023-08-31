<script setup lang="ts">
import { toRefs } from 'vue';

const props = withDefaults(
  defineProps<{
    text?: string;
    url: string;
  }>(),
  { text: '' }
);

const { url } = toRefs(props);
const { dark } = useTheme();

const { href, onLinkClick } = useLinks(url);
</script>

<template>
  <VTooltip top open-delay="600">
    <template #activator="{ on, attrs }">
      <VBtn
        small
        :icon="!text"
        :text="!!text"
        v-bind="attrs"
        color="primary"
        class="ml-2"
        :class="dark || text ? null : 'grey lighten-4'"
        :href="href"
        target="_blank"
        v-on="on"
        @click="onLinkClick()"
      >
        <span v-if="text" class="mr-2"> {{ text }}</span>
        <VIcon :small="true"> mdi-launch </VIcon>
      </VBtn>
    </template>
    <span>{{ url }}</span>
  </VTooltip>
</template>
