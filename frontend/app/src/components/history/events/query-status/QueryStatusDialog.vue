<script setup lang="ts">
defineProps<{
  items: any[];
  getKey: (item: any) => string;
  showTooltip?: (item: any) => boolean;
}>();

const { t } = useI18n();
const css = useCssModule();
</script>

<template>
  <v-dialog width="1200">
    <template #activator="{ on }">
      <v-btn text class="ml-4" v-on="on">
        {{ t('common.details') }}
        <v-icon small>mdi-chevron-right</v-icon>
      </v-btn>
    </template>
    <template #default="dialog">
      <v-card :class="css.card">
        <v-card-title class="d-flex justify-space-between pb-0">
          <div>
            <slot name="title" />
          </div>
          <v-btn icon @click="dialog.value = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <slot name="current" />

        <div class="px-6 pb-4">
          <div v-for="item in items" :key="getKey(item)" :class="css.item">
            <div class="d-flex align-center">
              <slot name="item" :item="item" />

              <v-tooltip v-if="showTooltip ? showTooltip(item) : true" bottom>
                <template #activator="{ on }">
                  <v-icon class="ml-2" v-on="on"> mdi-help-circle </v-icon>
                </template>

                <slot name="tooltip" :item="item" />
              </v-tooltip>
            </div>
            <slot name="steps" :item="item" />
          </div>
        </div>
      </v-card>
    </template>
  </v-dialog>
</template>

<style module lang="scss">
.item {
  padding: 1rem 0;
  border-top: 1px solid var(--v-rotki-light-grey-darken1);
}

.card {
  width: 100%;
  overflow: auto;
}
</style>
