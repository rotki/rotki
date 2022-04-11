<template>
  <v-tooltip open-delay="400" top>
    <template #activator="{ attrs, on }">
      <v-btn
        icon
        :small="small"
        v-bind="attrs"
        :href="$interop.isPackaged ? undefined : url"
        target="_blank"
        v-on="on"
        @click="$interop.isPackaged ? openLink() : undefined"
      >
        <v-icon :small="small">mdi-help-circle</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import { defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { interop } from '@/electron-interop';

export default defineComponent({
  name: 'HelpLink',
  props: {
    url: { required: true, type: String },
    tooltip: { required: true, type: String },
    small: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { url } = toRefs(props);

    const openLink = () => {
      interop.openUrl(get(url));
    };

    return {
      openLink
    };
  }
});
</script>
