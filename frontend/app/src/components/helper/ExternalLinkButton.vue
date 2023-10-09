<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    url?: string;
  }>(),
  {
    url: undefined
  }
);

const { url } = toRefs(props);
const { href, onLinkClick } = useLinks(url);
const attrs = useAttrs();

const { isPackaged } = useInterop();
</script>

<template>
  <RuiButton
    v-bind="{
      tag: 'button',
      type: 'button',
      ...attrs
    }"
    :href="href"
    :tag="href ? 'a' : 'button'"
    :target="isPackaged ? undefined : '_blank'"
    @click="onLinkClick()"
  >
    <template #prepend>
      <slot name="prepend" />
    </template>
    <slot />
    <template #append>
      <slot name="append" />
    </template>
  </RuiButton>
</template>
