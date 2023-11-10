<script lang="ts" setup>
const props = defineProps<{
  url: string;
}>();

const { url } = toRefs(props);
const { href, linkTarget, onLinkClick } = useLinks(url);
</script>

<template>
  <a :href="href" :target="linkTarget" @click="onLinkClick()"><slot /></a>
</template>
