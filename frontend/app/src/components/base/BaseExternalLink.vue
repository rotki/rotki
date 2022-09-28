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

<script setup lang="ts">
import { PropType } from 'vue';
import { useInterop } from '@/electron-interop';
import { truncateAddress } from '@/filters';
import { assert } from '@/utils/assertions';

const props = defineProps({
  href: {
    required: false,
    type: String as PropType<string | null | undefined>,
    default: null
  },
  truncate: { required: false, type: Boolean, default: false },
  text: { required: false, type: String, default: '' }
});

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
