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
  <RuiTooltip top open-delay="600">
    <template #activator="{ on, attrs }">
      <RuiButton
        size="sm"
        :icon="!text"
        v-bind="attrs"
        color="primary"
        variant="text"
        class="ml-2"
        :class="dark || text ? null : 'grey lighten-4'"
        :href="href"
        target="_blank"
        v-on="on"
        @click="onLinkClick()"
      >
        <span v-if="text" class="mr-2"> {{ text }}</span>
        <template #append>
          <RuiIcon name="external-link-line" size="20" />
        </template>
      </RuiButton>
    </template>
    <span>{{ url }}</span>
  </RuiTooltip>
</template>
