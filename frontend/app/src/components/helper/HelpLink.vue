<template>
  <v-tooltip open-delay="400" top>
    <template #activator="{ attrs, on }">
      <v-btn
        icon
        :small="small"
        v-bind="attrs"
        :href="href"
        target="_blank"
        v-on="on"
        @click="onLinkClick"
      >
        <v-icon :small="small">mdi-help-circle</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script setup lang="ts">
import { toRefs } from 'vue';
import { useLinks } from '@/composables/links';

const props = defineProps({
  url: { required: true, type: String },
  tooltip: { required: true, type: String },
  small: { required: false, type: Boolean, default: false }
});

const { url } = toRefs(props);
const { href, onLinkClick } = useLinks(url);
</script>
