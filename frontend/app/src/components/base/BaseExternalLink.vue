<template>
  <a
    v-if="href"
    :href="$interop.isPackaged ? undefined : href"
    target="_blank"
    class="text-no-wrap"
    @click="$interop.isPackaged ? openLink() : undefined"
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
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { interop } from '@/electron-interop';
import { truncateAddress } from '@/filters';

export default defineComponent({
  name: 'BaseExternalLink',
  props: {
    href: { required: false, type: String, default: null },
    truncate: { required: false, type: Boolean, default: false },
    text: { required: false, type: String, default: '' }
  },
  setup(props) {
    const { href, truncate, text } = toRefs(props);
    const openLink = () => {
      interop.openUrl(href.value);
    };

    const displayText = computed(() =>
      truncate.value ? truncateAddress(text.value) : text.value
    );

    return {
      openLink,
      displayText
    };
  }
});
</script>
