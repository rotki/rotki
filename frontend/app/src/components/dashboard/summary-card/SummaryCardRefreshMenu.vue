<script setup lang="ts">
const slots = useSlots();
const css = useCssModule();
</script>

<template>
  <div>
    <VMenu
      :disabled="!slots.refreshMenu"
      offset-y
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <RuiButton
          v-if="slots.refreshMenu"
          icon
          class="pa-0"
          :class="css['refresh-menu-activator']"
          v-on="on"
        >
          <VIcon>mdi-chevron-down</VIcon>
        </RuiButton>
      </template>
      <slot name="refreshMenu" />
    </VMenu>
  </div>
</template>

<style lang="scss" module>
.refresh-menu-activator {
  width: 20px !important;
  height: 20px !important;
}
</style>
