<template>
  <component :is="full ? 'full-size-content' : 'div'">
    <v-row align="center" justify="center" :class="{ 'mb-10': !full }">
      <v-col cols="auto" :class="$style.logo">
        <slot name="logo">
          <v-img
            contain
            :max-width="$vuetify.breakpoint.mobile ? '100px' : '200px'"
            src="/assets/images/rotkehlchen_no_text.png"
          />
        </slot>
      </v-col>
    </v-row>
    <v-row class="text-center">
      <v-col>
        <div v-if="$slots.title" class="text-h5">
          <slot name="title" />
        </div>
        <slot />
      </v-col>
    </v-row>
  </component>
</template>

<script setup lang="ts">
defineProps({
  full: { required: false, type: Boolean, default: true }
});
</script>

<style module lang="scss">
.logo {
  padding: 80px;
  border-radius: 50%;
  background-color: var(--v-rotki-light-grey-darken1);
}
</style>
