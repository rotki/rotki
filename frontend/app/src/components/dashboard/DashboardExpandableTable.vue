<script setup lang="ts">
const expanded = ref<boolean>(true);

const panel = computed<number>(() => (get(expanded) ? 0 : -1));
</script>
<template>
  <card :class="{ 'pb-4': expanded }">
    <template #title>
      <div class="d-flex align-center">
        <div class="mr-2">
          <v-btn
            text
            icon
            color="grey"
            class="px-0"
            rounded
            @click="expanded = !expanded"
          >
            <v-icon v-if="expanded">mdi-minus-box-outline</v-icon>
            <v-icon v-else>mdi-plus-box-outline</v-icon>
          </v-btn>
        </div>
        <div>
          <slot name="title" />
        </div>
      </div>
    </template>
    <template #details>
      <slot v-if="expanded" name="details" />
      <slot v-else name="shortDetails" />
    </template>
    <template #default>
      <v-expansion-panels :value="panel">
        <v-expansion-panel>
          <v-expansion-panel-content>
            <v-sheet outlined>
              <slot />
            </v-sheet>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </template>
  </card>
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
