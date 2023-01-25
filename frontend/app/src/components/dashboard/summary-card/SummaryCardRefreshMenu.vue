<script setup lang="ts">
withDefaults(
  defineProps<{
    name: string;
    canRefresh?: boolean;
    isLoading?: boolean;
  }>(),
  {
    canRefresh: false,
    isLoading: false
  }
);

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const refresh = () => emit('refresh');
const { t } = useI18n();

const slots = useSlots();
const css = useCssModule();
</script>

<template>
  <v-menu
    :disabled="!slots.refreshMenu"
    offset-y
    :close-on-content-click="false"
  >
    <template #activator="{ on }">
      <v-tooltip v-if="canRefresh" bottom max-width="300px">
        <template #activator="{ on: tooltipOn }">
          <v-btn
            icon
            small
            :disabled="isLoading"
            color="primary"
            @click="refresh"
            v-on="tooltipOn"
          >
            <v-icon small color="primary">mdi-refresh</v-icon>
          </v-btn>
        </template>
        <span>
          {{ t('summary_card.refresh_tooltip', { name }) }}
        </span>
      </v-tooltip>

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
</template>

<style lang="scss" module>
.refresh-menu-activator {
  width: 20px !important;
  height: 20px !important;
}
</style>
