<template>
  <a href="#" @click="onLinkClick()"><slot /></a>
</template>

<script setup lang="ts">
import { useLinks } from '@/composables/links';

const props = defineProps({
  url: { required: true, type: String }
});

const { url } = toRefs(props);
const { onLinkClick } = useLinks(url);
</script>
