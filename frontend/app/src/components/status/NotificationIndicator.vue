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
      :tooltip="tc('notification_indicator.tooltip')"
      class-name="secondary--text text--lighten-4"
      @click="click"
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

<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { setupNotifications } from '@/composables/notifications';
import { setupTaskStatus } from '@/composables/tasks';

defineProps({
  visible: { required: true, type: Boolean }
});

const emit = defineEmits(['click']);
const { count } = setupNotifications();
const click = () => {
  emit('click');
};

const { hasRunningTasks } = setupTaskStatus();

const { tc } = useI18n();
</script>

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
