<script setup lang="ts">
const slots = useSlots();
const css = useCssModule();
</script>

<template>
  <div>
    <v-menu
      :disabled="!slots.refreshMenu"
      offset-y
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <v-btn
          v-if="slots.refreshMenu"
          icon
          depressed
          fab
          x-small
          class="pa-0"
          :class="css['refresh-menu-activator']"
          v-on="on"
        >
          <v-icon>mdi-chevron-down</v-icon>
        </v-btn>
      </template>
      <slot name="refreshMenu" />
    </v-menu>
  </div>
</template>

<style lang="scss" module>
.refresh-menu-activator {
  width: 20px !important;
  height: 20px !important;
}
</style>
