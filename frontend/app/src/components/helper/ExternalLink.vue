<script lang="ts" setup>
const props = defineProps({
  url: { required: true, type: String }
});

const { url } = toRefs(props);
const { onLinkClick } = useLinks(url);
</script>

<template>
  <a href="#" @click.prevent="onLinkClick()"><slot /></a>
</template>
