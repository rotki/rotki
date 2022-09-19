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
        target="_blank"
        v-on="on"
        @click="onLinkClick"
      >
        <span v-if="text" class="mr-2"> {{ text }}</span>
        <v-icon :small="true"> mdi-launch </v-icon>
      </v-btn>
    </template>
    <span>{{ url }}</span>
  </v-tooltip>
</template>

<script setup lang="ts">
import { toRefs } from 'vue';
import { useTheme } from '@/composables/common';
import { useLinks } from '@/composables/links';

const props = defineProps({
  text: {
    type: String,
    required: false,
    default: ''
  },
  url: {
    type: String,
    required: true
  }
});

const { url } = toRefs(props);
const { dark } = useTheme();

const { href, onLinkClick } = useLinks(url);
</script>
