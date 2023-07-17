<script setup lang="ts">
withDefaults(defineProps<{ full?: boolean }>(), { full: true });

const FullSizeContent = defineAsyncComponent(
  () => import('@/components/common/FullSizeContent.vue')
);

const slots = useSlots();
const css = useCssModule();
const { mobile } = useDisplay();
const remoteEmptyScreenLogo =
  'https://raw.githubusercontent.com/rotki/data/main/assets/icons/empty_screen_logo.png';
</script>

<template>
  <Component :is="full ? FullSizeContent : 'div'">
    <VRow align="center" justify="center" :class="{ 'mb-10': !full }">
      <VCol cols="auto" :class="css.logo">
        <slot name="logo">
          <RotkiLogo
            :width="mobile ? '100px' : '200px'"
            :url="remoteEmptyScreenLogo"
          />
        </slot>
      </VCol>
    </VRow>
    <VRow class="text-center">
      <VCol>
        <div v-if="slots.title" class="text-h5">
          <slot name="title" />
        </div>
        <slot />
      </VCol>
    </VRow>
  </Component>
</template>

<style module lang="scss">
.logo {
  padding: 80px;
  border-radius: 50%;
  background-color: var(--v-rotki-light-grey-darken1);
}
</style>
