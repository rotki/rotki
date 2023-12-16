<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    text?: string;
    url: string;
  }>(),
  { text: '' },
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
        size="sm"
        variant="text"
        :icon="!text"
        :text="!!text"
        color="primary"
        tag="a"
        :href="href"
        target="_blank"
        @click="onLinkClick()"
      >
        <span v-if="text">
          {{ text }}
        </span>
        <template #append>
          <RuiIcon
            name="external-link-line"
            :size="16"
          />
        </template>
      </RuiButton>
    </template>
    <span>{{ url }}</span>
  </RuiTooltip>
</template>
