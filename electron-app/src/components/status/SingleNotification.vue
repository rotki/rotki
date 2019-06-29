<template>
  <div :id="`notification-${notification.id}`" class="notification card card-1">
    <div>
      <div class="title">{{ notification.title }}</div>
      <div class="body">
        {{ notification.message }}
      </div>
    </div>
    <div class="icons">
      <div data-tooltip="Dismisses notification" class="tooltip-left">
        <v-icon class="notification-dismiss">fa fa-close fa-2x</v-icon>
      </div>
      <v-icon :class="colorClass(notification)">
        fa {{ icon(notification) }} fa-2x
      </v-icon>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { NotificationData, Severity } from '@/typing/types';

@Component({})
export default class SingleNotification extends Vue {
  @Prop({ required: true })
  notification!: NotificationData;

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

  colorClass(notification: NotificationData) {
    switch (notification.severity) {
      case Severity.ERROR:
        return 'text-danger';
      case Severity.INFO:
        return 'text-info';
      case Severity.WARNING:
        return 'text-warning';
    }
  }
}
</script>

<style scoped lang="scss">
.title {
  font-size: 1.4rem;
  padding: 8px 8px;
  font-weight: 500;
}

.body {
  padding: 4px 8px;
  word-wrap: break-word;
  font-size: 1.3rem;
  color: rgba(0, 0, 0, 0.56);
}

.card {
  background: #fff;
  border-radius: 2px;
  display: inline-block;
  height: 120px;
  margin: 0.5rem 1rem;
  position: relative;
  width: 300px;
}

.card-1 {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.notification {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  padding: 6px;
}

.notification:first-child {
  flex-grow: 1;
}

.notification .icons {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  color: #757575;
  padding-left: 4px;
}

.notification .icons .icon {
  margin-bottom: 40px;
}
</style>
