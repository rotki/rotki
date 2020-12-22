<template>
  <v-badge
    :value="count"
    color="primary"
    right
    overlap
    class="notification-indicator"
  >
    <template #badge>
      <span>{{ count }}</span>
    </template>
    <menu-tooltip-button
      :tooltip="$t('notification_indicator.tooltip')"
      class-name="secondary--text text--lighten-2"
      @click="click"
    >
      <v-icon :class="visible ? 'notification-indicator--visible' : null">
        mdi-bell
      </v-icon>
    </menu-tooltip-button>
  </v-badge>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

@Component({
  computed: {
    ...mapGetters('notifications', ['count'])
  },
  components: {
    MenuTooltipButton
  }
})
export default class NotificationIndicator extends Vue {
  count!: number;

  @Prop({ required: true, type: Boolean })
  visible!: boolean;

  @Emit()
  click() {}
}
</script>

<style scoped lang="scss">
.notification-indicator {
  ::v-deep {
    .v-badge {
      &__badge {
        bottom: calc(100% - 20px) !important;
        left: calc(100% - 20px) !important;
      }
    }
  }

  &--visible {
    transform: rotate(-25deg);
  }
}
</style>
