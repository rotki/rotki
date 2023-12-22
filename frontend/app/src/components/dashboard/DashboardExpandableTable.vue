<script setup lang="ts">
const expanded = ref<boolean>(true);

const panel = computed<number>(() => (get(expanded) ? 0 : -1));
</script>

<template>
  <RuiCard :class="{ '[&>div:last-child]:!py-0': !expanded }">
    <template #custom-header>
      <div class="flex justify-between items-center flex-wrap p-4 gap-2">
        <CardTitle>
          <RuiButton variant="text" icon @click="expanded = !expanded">
            <RuiIcon
              :name="expanded ? 'checkbox-indeterminate-line' : 'add-box-line'"
            />
          </RuiButton>
          <slot name="title" />
        </CardTitle>

        <div class="flex items-center gap-2 grow justify-end">
          <slot v-if="expanded" name="details" />
          <slot v-else name="shortDetails" />
        </div>
      </div>
    </template>
    <VExpansionPanels :value="panel">
      <VExpansionPanel>
        <VExpansionPanelContent>
          <slot />
        </VExpansionPanelContent>
      </VExpansionPanel>
    </VExpansionPanels>
  </RuiCard>
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
