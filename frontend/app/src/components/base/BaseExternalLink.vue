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

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { useInterop } from '@/electron-interop';
import { truncateAddress } from '@/filters';
import { assert } from '@/utils/assertions';

export default defineComponent({
  name: 'BaseExternalLink',
  props: {
    href: {
      required: false,
      type: String as PropType<string | null | undefined>,
      default: null
    },
    truncate: { required: false, type: Boolean, default: false },
    text: { required: false, type: String, default: '' }
  },
  setup(props) {
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

    return {
      openLink,
      isPackaged,
      displayText
    };
  }
});
</script>
