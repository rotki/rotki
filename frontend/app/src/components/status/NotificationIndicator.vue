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
      :tooltip="$t('notification_indicator.tooltip')"
      class-name="secondary--text text--lighten-2"
      @click="click"
    >
      <v-icon
        :class="{
          [$style.visible]: visible
        }"
      >
        mdi-bell
      </v-icon>
    </menu-tooltip-button>
  </v-badge>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { setupNotifications } from '@/composables/notifications';

const NotificationIndicator = defineComponent({
  name: 'NotificationIndicator',
  components: {
    MenuTooltipButton
  },
  props: {
    visible: { required: true, type: Boolean }
  },
  emits: ['click'],
  setup(_, { emit }) {
    const { count } = setupNotifications();
    const click = () => {
      emit('click');
    };
    return {
      click,
      count
    };
  }
});
export default NotificationIndicator;
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
