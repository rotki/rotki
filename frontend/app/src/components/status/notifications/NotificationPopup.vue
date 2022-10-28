<template>
  <v-snackbar
    v-model="visibleNotification.display"
    :class="$style.popup"
    :timeout="visibleNotification.duration"
    top
    right
    :light="!$vuetify.theme.dark"
    app
    rounded
    width="400px"
    @input="displayed([visibleNotification.id])"
  >
    <notification
      popup
      :notification="visibleNotification"
      @dismiss="dismiss(visibleNotification.id)"
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
          <span>{{ t('notification_popup.dismiss_all') }}</span>
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
      <span v-text="t('notification_popup.tooltip')" />
    </v-tooltip>
  </v-snackbar>
</template>

<script setup lang="ts">
import Notification from '@/components/status/notifications/Notification.vue';
import { setupNotifications } from '@/composables/notifications';
import { emptyNotification } from '@/store/notifications';

const visibleNotification = ref(emptyNotification());
const { queue, displayed } = setupNotifications();
const dismiss = async (id: number) => {
  await displayed([id]);
  set(visibleNotification, { ...get(visibleNotification), display: false });
};

const dismissAll = async () => {
  await displayed(get(queue).map(({ id }) => id));
  set(visibleNotification, { ...get(visibleNotification), display: false });
};

watch(
  queue,
  () => {
    const data = [...get(queue)];
    if (!get(visibleNotification).display && data.length > 0) {
      const next = data.shift();
      if (!next) {
        return;
      }
      nextTick(() => {
        set(visibleNotification, next);
      });
    }
  },
  { deep: true }
);

const { t } = useI18n();
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
