<script setup lang="ts">
defineProps({
  visible: { required: true, type: Boolean }
});

const emit = defineEmits(['click']);
const { count } = storeToRefs(useNotificationsStore());
const click = () => {
  emit('click');
};

const { hasRunningTasks } = storeToRefs(useTaskStore());

const { t } = useI18n();
</script>

<template>
  <v-badge
    :value="count"
    color="primary"
    right
    overlap
    :class="$style.indicator"
  >
    <template #badge>
      <span>{{ count }}</span>
    </template>
    <menu-tooltip-button
      :tooltip="t('notification_indicator.tooltip')"
      class-name="secondary--text text--lighten-4"
      @click="click()"
    >
      <v-icon
        v-if="!hasRunningTasks"
        :class="{
          [$style.visible]: visible
        }"
      >
        mdi-bell
      </v-icon>
      <v-icon v-else> mdi-spin mdi-loading </v-icon>
    </menu-tooltip-button>
  </v-badge>
</template>

<style module lang="scss">
.indicator {
  :global {
    .v-badge {
      &__badge {
        bottom: calc(100% - 20px) !important;
        left: calc(100% - 20px) !important;
      }
    }
  }
}

.visible {
  transform: rotate(-25deg);
}
</style>
