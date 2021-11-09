<template>
  <v-tooltip top open-delay="600">
    <template #activator="{ on, attrs }">
      <v-btn
        small
        :icon="!text"
        :text="!!text"
        v-bind="attrs"
        color="primary"
        class="ml-2"
        :class="dark || text ? null : 'grey lighten-4'"
        :href="href"
        :target="target"
        v-on="on"
        @click="openLink"
      >
        <span v-if="text" class="mr-2"> {{ text }}</span>
        <v-icon :small="true"> mdi-launch </v-icon>
      </v-btn>
    </template>
    <span>{{ url }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { interop } from '@/electron-interop';
import ThemeMixin from '@/mixins/theme-mixin';

export default defineComponent({
  name: 'IconLink',
  mixins: [ThemeMixin],
  props: {
    text: {
      type: String,
      required: false,
      default: ''
    },
    url: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const { url } = toRefs(props);
    const openLink = () => {
      interop.openUrl(url.value);
    };

    const target = interop.isPackaged ? undefined : '_blank';

    const href = computed(() => {
      if (interop.isPackaged) {
        return undefined;
      }
      return url.value;
    });

    return {
      openLink,
      target,
      href
    };
  }
});
</script>
