<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    url?: string;
    truncate?: boolean;
    text?: string;
    custom?: boolean;
    premium?: boolean;
  }>(),
  {
    url: undefined,
    truncate: false,
    text: '',
    custom: false,
    premium: false
  }
);

const { url, truncate, text } = toRefs(props);
const { isPackaged } = useInterop();

const { href, linkTarget, onLinkClick } = useLinks(url);

const displayText = computed(() =>
  get(truncate) ? truncateAddress(get(text)) : get(text)
);

const attrs = useAttrs();
const css = useCssModule();
</script>

<template>
  <RuiButton
    v-if="(url || premium) && !custom"
    :tag="isPackaged ? 'button' : 'a'"
    :href="href"
    :target="linkTarget"
    v-bind="attrs"
    variant="text"
    :class="css.button"
    @click="onLinkClick()"
  >
    <slot>{{ displayText }}</slot>
  </RuiButton>
  <a
    v-else-if="url || premium"
    :href="href"
    :target="linkTarget"
    class="text-no-wrap"
    @click="onLinkClick()"
  >
    <slot>{{ displayText }}</slot>
  </a>
  <div v-else>
    <slot />
  </div>
</template>

<style lang="scss" module>
.button {
  font-weight: inherit !important;

  span {
    @apply underline;
  }

  @apply inline text-[1em] p-0 px-0.5 -mx-0.5 #{!important};
}
</style>
