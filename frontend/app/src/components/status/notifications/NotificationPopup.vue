<template>
  <v-snackbar
    v-model="notification.display"
    class="notification-popup"
    :timeout="notification.duration"
    top
    right
    app
    rounded
    width="400px"
    @input="displayed(notification.id)"
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
        <div class="notification-popup__count__wrapper" v-on="on">
          <v-badge
            inline
            :content="queue.length"
            color="info"
            class="notification-popup__count"
          />
        </div>
      </template>
      <span v-text="$t('notification_popup.tooltip')" />
    </v-tooltip>
  </v-snackbar>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import Notification from '@/components/status/notifications/Notification.vue';
import { NotificationData } from '@/store/notifications/types';
import { emptyNotification } from '@/store/notifications/utils';

@Component({
  components: { Notification },
  computed: {
    ...mapGetters('notifications', ['queue'])
  },
  methods: {
    ...mapActions('notifications', ['displayed'])
  }
})
export default class NotificationPopup extends Vue {
  notification: NotificationData = emptyNotification();
  queue!: NotificationData[];
  displayed!: (id: number[]) => void;

  @Watch('queue', { deep: true })
  onQueueUpdate() {
    if (!this.notification.display && this.queue.length > 0) {
      const nextNotification = this.queue.shift();
      if (!nextNotification) {
        return;
      }
      this.$nextTick(() => (this.notification = nextNotification));
    }
  }

  dismiss(id: number) {
    this.displayed([id]);
    this.notification = { ...this.notification, display: false };
  }

  dismissAll() {
    this.displayed(this.queue.map(({ id }) => id));
    this.notification = { ...this.notification, display: false };
  }
}
</script>
<style scoped lang="scss">
.notification-popup {
  ::v-deep {
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

  &__count {
    position: absolute;
    right: 4px;
    top: 0;

    &__wrapper {
      position: absolute;
      top: 48px;
      right: 0;
    }
  }
}
</style>
