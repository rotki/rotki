<template>
  <v-btn :icon="icon" :text="text" @click="navigateToDetails">
    <slot />
  </v-btn>
</template>

<script setup lang="ts">
import { useRouter } from '@/composables/router';
import { Routes } from '@/router/routes';

const props = defineProps({
  asset: { required: true, type: String },
  icon: { required: false, default: false, type: Boolean },
  text: { required: false, default: false, type: Boolean }
});

const { asset } = toRefs(props);

const router = useRouter();

const navigateToDetails = async () => {
  await router.push({
    path: Routes.ASSETS.route.replace(
      ':identifier',
      encodeURIComponent(get(asset))
    )
  });
};
</script>
