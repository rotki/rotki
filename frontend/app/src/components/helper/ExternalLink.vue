<script lang="ts" setup>
const props = defineProps<{
  url: string;
}>();

const { url } = toRefs(props);
const { onLinkClick } = useLinks(url);
</script>

<template>
  <a href="#" @click.prevent="onLinkClick()"><slot /></a>
</template>
