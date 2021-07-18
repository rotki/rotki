<template>
  <v-card class="notification" :outlined="!popup" :elevation="0">
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
        <span class="notification__message mt-1" :style="fontStyle">
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
        <slot />
      </v-list-item-content>
      <v-col cols="auto">
        <div class="d-flex flex-column">
          <v-tooltip bottom open-delay="400">
            <template #activator="{ on }">
              <v-btn
                text
                icon
                class="notification__dismiss"
                v-on="on"
                @click="dismiss(notification.id)"
              >
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </template>
            <span v-text="$t('notification.dismiss_tooltip')" />
          </v-tooltip>
          <v-tooltip bottom open-delay="400">
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
            <span v-text="$t('notification.copy_tooltip')" />
          </v-tooltip>
        </div>
      </v-col>
    </v-list-item>
  </v-card>
</template>

<script lang="ts">
import dayjs from 'dayjs';
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import ThemeMixin from '@/mixins/theme-mixin';
import { Severity } from '@/store/notifications/consts';
import { NotificationData } from '@/store/notifications/types';
@Component({
  components: {}
})
export default class Notification extends Mixins(ThemeMixin) {
  @Prop({ required: true })
  notification!: NotificationData;
  @Prop({ required: false, type: Boolean, default: false })
  popup!: boolean;

  @Emit()
  dismiss(_notificationId: number) {}

  icon(notification: NotificationData) {
    switch (notification.severity) {
      case Severity.ERROR:
        return 'mdi-alert-circle';
      case Severity.INFO:
        return 'mdi-information-outline';
      case Severity.WARNING:
        return 'mdi-alert';
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
    return dayjs(date).format('LLL');
  }
}
</script>
<style scoped lang="scss">
.notification {
  height: 120px;
  max-width: 400px;

  &__body {
    height: 100% !important;
  }

  &__message {
    font-size: 13px;
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
