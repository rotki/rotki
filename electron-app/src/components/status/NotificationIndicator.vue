<template>
  <v-menu transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-badge color="accent" right overlap>
        <template #badge>
          <span>{{ count }}</span>
        </template>
        <v-btn color="primary" dark icon text v-on="on">
          <v-icon>
            fa fa-bell
          </v-icon>
        </v-btn>
      </v-badge>
      <confirm-dialog
        :display="confirmClear"
        title="Clear active notifications"
        message="This action will clear all the active notifications. Do you want to proceed?"
        @cancel="confirmClear = false"
        @confirm="clear()"
      ></confirm-dialog>
    </template>
    <v-row class="notification-indicator__details">
      <v-col v-if="false" class="notification-indicator__no-messages">
        <v-icon color="primary">fa fa-info-circle</v-icon>
        <p class="notification-indicator__no-messages__label">No messages!</p>
      </v-col>
      <v-col v-else class="notification-indicator__messages">
        <v-list two-line>
          <div class="notification-indicator__messages__clear">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  text
                  icon
                  color="primary"
                  class="notification-indicator__clear"
                  v-on="on"
                  @click="confirmClear = true"
                >
                  <v-icon id="notifications-clear-all">
                    fa fa-trash
                  </v-icon>
                </v-btn>
              </template>
              <span>
                Clears all notifications
              </span>
            </v-tooltip>
          </div>
          <template v-for="notification in notifications">
            <v-list-item :key="notification.id">
              <v-list-item-content>
                <v-list-item-title
                  v-text="notification.title"
                ></v-list-item-title>
                <span class="notification-indicator__messages__message">
                  {{ notification.message }}
                </span>
              </v-list-item-content>
              <v-list-item-action>
                <v-list-item-action-text>
                  <v-tooltip bottom>
                    <template #activator="{ on }">
                      <v-btn text icon v-on="on" @click="dismiss(notification)">
                        <v-icon>fa fa-close</v-icon>
                      </v-btn>
                    </template>
                    <span>
                      Dismisses Notification
                    </span>
                  </v-tooltip>
                </v-list-item-action-text>
                <v-icon :color="color(notification)">
                  {{ icon(notification) }}
                </v-icon>
              </v-list-item-action>
            </v-list-item>

            <v-divider :key="`notification-${notification.id}`"></v-divider>
          </template>
        </v-list>
      </v-col>
    </v-row>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { NotificationData, Severity } from '@/typing/types';
import { createNamespacedHelpers } from 'vuex';
import orderBy from 'lodash/orderBy';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';

const { mapState, mapGetters, mapMutations } = createNamespacedHelpers(
  'notifications'
);

@Component({
  computed: {
    ...mapState(['data']),
    ...mapGetters(['count']),
    ...mapMutations(['remove', 'reset'])
  },
  components: {
    ConfirmDialog
  }
})
export default class NotificationIndicator extends Vue {
  data!: NotificationData[];
  count!: number;
  remove!: (id: number) => void;
  reset!: () => void;

  confirmClear: boolean = false;

  icon(notification: NotificationData) {
    switch (notification.severity) {
      case Severity.ERROR:
        return 'fa-exclamation-circle';
      case Severity.INFO:
        return 'fa-info-circle';
      case Severity.WARNING:
        return 'fa-exclamation-triangle';
    }
  }

  color(notification: NotificationData) {
    switch (notification.severity) {
      case Severity.ERROR:
        return 'error';
      case Severity.INFO:
        return 'info';
      case Severity.WARNING:
        return 'warning';
    }
  }

  get notifications(): NotificationData[] {
    return orderBy(this.data, 'id', 'desc');
  }

  dismiss(notification: NotificationData) {
    this.remove(notification.id);
  }
}
</script>

<style scoped lang="scss">
.notification-indicator__details {
  width: 400px;
  height: 350px;
  background-color: white;
  overflow-y: scroll;
  font-weight: 400;
  color: rgba(0, 0, 0, 0.87);
}

.notification-indicator__no-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.notification-indicator__no-messages__label {
  font-size: 22px;
  margin-top: 22px;
  font-weight: 300;
  color: rgb(0, 0, 0, 0.6);
}

.notification-indicator__messages {
  padding-right: 0 !important;
}

.notification-indicator__messages__clear {
  display: flex;
  flex-direction: row-reverse;
  padding-right: 8px;
}

.notification-indicator__messages__message {
  font-size: 13px;
  color: rgb(0, 0, 0, 0.6);
}

::v-deep .v-badge__badge {
  top: 0 !important;
  right: 0 !important;
}

::v-deep .v-list-item__action-text {
  margin-right: -8px;
  margin-top: -8px;
}
</style>
