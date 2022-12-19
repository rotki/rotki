<script setup lang="ts">
const props = defineProps({
  url: { required: true, type: String }
});

const { url } = toRefs(props);
const { onLinkClick } = useLinks(url);
</script>

<template>
  <a href="#" @click="onLinkClick()"><slot /></a>
</template>
