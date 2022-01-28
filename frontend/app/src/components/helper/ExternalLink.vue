<template>
  <a href="#" @click="openLink()"><slot /></a>
</template>

<script lang="ts">
import { defineComponent, toRefs } from '@vue/composition-api';
import { interop } from '@/electron-interop';

export default defineComponent({
  name: 'ExternalLink',
  props: {
    url: { required: true, type: String }
  },
  setup(props) {
    const { url } = toRefs(props);
    const openLink = () => {
      interop.openUrl(url.value);
    };

    return { openLink };
  }
});
</script>
