<template>
  <a href="#" @click="openLink()"><slot /></a>
</template>

<script lang="ts">
import { defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { interop } from '@/electron-interop';

export default defineComponent({
  name: 'ExternalLink',
  props: {
    url: { required: true, type: String }
  },
  setup(props) {
    const { url } = toRefs(props);
    const openLink = () => {
      interop.openUrl(get(url));
    };

    return { openLink };
  }
});
</script>
