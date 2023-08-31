<script setup lang="ts">
const expanded = ref<boolean>(true);

const panel = computed<number>(() => (get(expanded) ? 0 : -1));
</script>

<template>
  <Card :class="{ 'pb-6': expanded }">
    <template #title>
      <div class="d-flex align-center">
        <div class="mr-2">
          <VBtn
            text
            icon
            color="grey"
            class="px-0"
            rounded
            @click="expanded = !expanded"
          >
            <VIcon v-if="expanded">mdi-minus-box-outline</VIcon>
            <VIcon v-else>mdi-plus-box-outline</VIcon>
          </VBtn>
        </div>
        <div class="flex items-center gap-x-2">
          <slot name="title" />
        </div>
      </div>
    </template>
    <template #details>
      <slot v-if="expanded" name="details" />
      <slot v-else name="shortDetails" />
    </template>
    <template #default>
      <VExpansionPanels :value="panel">
        <VExpansionPanel>
          <VExpansionPanelContent>
            <slot />
          </VExpansionPanelContent>
        </VExpansionPanel>
      </VExpansionPanels>
    </template>
  </Card>
</template>

<style scoped lang="scss">
:deep(.v-expansion-panel) {
  &::before {
    box-shadow: none;
  }

  .v-expansion-panel {
    &-content {
      &__wrap {
        padding: 0 !important;
      }
    }
  }
}

/* stylelint-disable selector-class-pattern,selector-nested-pattern */

:deep(.v-card__text) {
  padding-bottom: 0 !important;
}
/* stylelint-enable selector-class-pattern,selector-nested-pattern */
</style>
