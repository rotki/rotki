<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    href?: string | null;
    truncate?: boolean;
    text?: string;
  }>(),
  { href: null, truncate: false, text: '' }
);

const { href, truncate, text } = toRefs(props);
const { openUrl, isPackaged } = useInterop();
const openLink = () => {
  const url = get(href);
  assert(url);
  openUrl(url);
};

const displayText = computed(() =>
  get(truncate) ? truncateAddress(get(text)) : get(text)
);
</script>

<template>
  <a
    v-if="href"
    :href="isPackaged ? undefined : href"
    target="_blank"
    class="text-no-wrap"
    @click="isPackaged ? openLink() : undefined"
  >
    <slot>
      {{ displayText }}
    </slot>
  </a>
  <div v-else>
    <slot />
  </div>
</template>
