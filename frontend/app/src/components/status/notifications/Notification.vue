<template>
  <v-card class="notification" outlined>
    <v-list-item class="notification__body">
      <v-list-item-avatar>
        <v-icon
          size="32px"
          :color="color(notification)"
          class="notification__severity"
        >
          {{ icon(notification) }}
        </v-icon>
      </v-list-item-avatar>
      <v-list-item-content>
        <v-list-item-title class="mt-2">
          {{ notification.title }}
        </v-list-item-title>
        <span class="notification__message mt-1">
          {{ notification.message }}
          <textarea
            ref="copy"
            class="notification__copy-area"
            :value="notification.message"
          />
        </span>
        <span class="text-caption text--secondary">
          {{ timeDisplay(notification.date) }}
        </span>
      </v-list-item-content>
      <v-col cols="auto">
        <div class="d-flex flex-column">
          <v-tooltip bottom>
            <template #activator="{ on }">
              <v-btn
                text
                icon
                class="notification__dismiss"
                v-on="on"
                @click="dismiss(notification)"
              >
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </template>
            <span>
              Dismiss Notification
            </span>
          </v-tooltip>
          <v-tooltip bottom>
            <template #activator="{ on }">
              <v-btn
                class="notification__copy"
                text
                icon
                v-on="on"
                @click="copy"
              >
                <v-icon>mdi-content-copy</v-icon>
              </v-btn>
            </template>
            <span>Copy the message to clipboard</span>
          </v-tooltip>
        </div>
      </v-col>
    </v-list-item>
  </v-card>
</template>

<script lang="ts">
import moment from 'moment';
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { Severity } from '@/store/notifications/consts';
import { NotificationData } from '@/store/notifications/types';
@Component({
  components: {}
})
export default class Notification extends Vue {
  @Prop({ required: true })
  notification!: NotificationData;

  @Emit()
  dismiss(_notificationId: number) {}

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

  copy() {
    const copy = this.$refs.copy as HTMLTextAreaElement;
    copy.focus();
    copy.select();
    document.execCommand('copy');
    copy.blur();
  }

  timeDisplay(date: Date): string {
    return moment(date).format('LLL');
  }
}
</script>
<style scoped lang="scss">
.notification {
  height: 120px;

  &__body {
    height: 100% !important;
  }

  &__message {
    font-size: 13px;
    color: rgb(0, 0, 0, 0.6);
    min-height: 60px;
    max-height: 60px;
    overflow-y: auto;
  }

  &__dismiss {
    position: absolute;
    right: 0;
    top: 0;
  }

  &__copy {
    position: absolute;
    right: 0;
    bottom: 4px;
  }

  &__copy-area {
    position: absolute;
    left: -999em;
  }
}
</style>
