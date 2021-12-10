<template>
  <v-snackbar
    v-model="notification.display"
    :class="$style.popup"
    :timeout="notification.duration"
    top
    right
    :light="!$vuetify.theme.dark"
    app
    rounded
    width="400px"
    @input="displayed([notification.id])"
  >
    <notification
      popup
      :notification="notification"
      @dismiss="dismiss(notification.id)"
    />
    <v-divider />
    <v-row v-if="queue.length > 0" justify="end">
      <v-col cols="auto">
        <v-tooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <v-btn icon v-bind="attrs" v-on="on" @click="dismissAll()">
              <v-icon>mdi-notification-clear-all</v-icon>
            </v-btn>
          </template>
          <span>{{ $t('notification_popup.dismiss_all') }}</span>
        </v-tooltip>
      </v-col>
    </v-row>
    <v-tooltip v-if="queue.length > 0" bottom>
      <template #activator="{ on }">
        <div :class="$style.wrapper" v-on="on">
          <v-badge
            inline
            :content="queue.length"
            color="info"
            :class="$style.count"
          />
        </div>
      </template>
      <span v-text="$t('notification_popup.tooltip')" />
    </v-tooltip>
  </v-snackbar>
</template>

<script lang="ts">
import { defineComponent, nextTick, ref, watch } from '@vue/composition-api';
import Notification from '@/components/status/notifications/Notification.vue';
import { setupNotifications } from '@/composables/notifications';
import { emptyNotification } from '@/store/notifications';

const NotificationPopup = defineComponent({
  name: 'NotificationPopup',
  components: { Notification },
  setup() {
    const notification = ref(emptyNotification());
    const { queue, displayed } = setupNotifications();
    const dismiss = (id: number) => {
      displayed([id]);
      notification.value = { ...notification.value, display: false };
    };

    const dismissAll = () => {
      displayed(queue.value.map(({ id }) => id));
      notification.value = { ...notification.value, display: false };
    };

    watch(
      queue,
      () => {
        const data = [...queue.value];
        if (!notification.value.display && data.length > 0) {
          const next = data.shift();
          if (!next) {
            return;
          }
          nextTick(() => {
            notification.value = next;
          });
        }
      },
      { deep: true }
    );
    return {
      queue,
      notification,
      dismiss,
      dismissAll,
      displayed
    };
  }
});
export default NotificationPopup;
</script>
<style module lang="scss">
.popup {
  :global {
    .v-snack {
      &__wrapper {
        width: 400px;
      }

      &__content {
        padding: 0 !important;
      }

      &__action {
        margin-right: 0 !important;
      }
    }
  }
}

.count {
  position: absolute;
  right: 4px;
  top: 0;
}

.wrapper {
  position: absolute;
  top: 48px;
  right: 0;
}
</style>
