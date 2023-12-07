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
  <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
    <template #activator>
      <RuiButton
        size="sm"
        variant="text"
        :icon="!text"
        :text="!!text"
        color="primary"
        class="ml-2"
        tag="a"
        :class="dark || text ? null : 'grey lighten-4'"
        :href="href"
        target="_blank"
        @click="onLinkClick()"
      >
        <span v-if="text" class="mr-2"> {{ text }}</span>
        <template #append>
          <RuiIcon name="external-link-line" :size="16" />
        </template>
      </RuiButton>
    </template>
    <span>{{ url }}</span>
  </RuiTooltip>
</template>
