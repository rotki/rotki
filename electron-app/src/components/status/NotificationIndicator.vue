<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-menu id="notification-indicator" transition="slide-y-transition" bottom>
    <template v-slot:activator="{ on }">
      <v-badge color="primary" right overlap>
        <template v-slot:badge>
          <span>{{ count }}</span>
        </template>
        <v-btn color="primary" dark icon flat v-on="on">
          <v-icon>
            fa fa-bell fa-fw
          </v-icon>
          <v-icon>fa fa-caret-down</v-icon>
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
    <v-layout id="notification-messages" column class="popup">
      <div v-if="count === 0" class="no-notifications">
        <v-icon>fa fa-info-circle fa-fw</v-icon>
        <p>No messages!</p>
      </div>
      <div v-else>
        <div
          class="notification-clear tooltip-right"
          data-tooltip="Clears all notifications"
          @click="confirmClear = true"
        >
          <v-icon id="notifications-clear-all">fa fa-trash fa-1x</v-icon>
        </div>
        <div class="notification-area">
          <single-notification
            v-for="notification in notifications"
            :notification="notification"
            @click="dismiss(notification)"
          ></single-notification>
        </div>
      </div>
    </v-layout>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { NotificationData } from '@/typing/types';
import { createNamespacedHelpers } from 'vuex';
import SingleNotification from '@/components/status/SingleNotification.vue';
import orderBy from 'lodash/orderBy';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';

const { mapState, mapGetters, mapMutations } = createNamespacedHelpers(
  'notifications'
);

@Component({
  computed: {
    ...mapState(['data']),
    ...mapGetters(['count']),
    ...mapMutations(['remove', 'clear'])
  },
  components: {
    SingleNotification,
    ConfirmDialog
  }
})
export default class NotificationIndicator extends Vue {
  data!: NotificationData[];
  count!: number;
  remove!: (id: number) => void;
  clear!: () => void;

  confirmClear: boolean = false;

  get notifications(): NotificationData[] {
    return orderBy(this.data, 'id', 'desc');
  }

  dismiss(notification: NotificationData) {
    this.remove(notification.id);
  }
}
</script>

<style scoped lang="scss">
.popup {
  padding: 16px;
}
.no-notifications {
  height: 80%;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: rgba(0, 0, 0, 0.57);
}

.no-notifications p {
  margin-top: 8px;
}

#notification-messages {
  background-color: white;
}

.notification-clear {
  display: flex;
  flex-direction: row-reverse;
  background: var(--notification-background);
}

.notification-clear > * {
  padding: 8px;
  color: var(--elements-bg-color);
}

.notification-area {
  width: 340px;
  height: 300px;
  background: var(--notification-background);
  overflow-y: scroll;
  overflow-x: hidden;
  font-family: Roboto, sans-serif;
  font-size: 1rem;
  line-height: 1.75rem;
  font-weight: 400;
  letter-spacing: 0.009375em;
  list-style-type: none;
  color: rgba(0, 0, 0, 0.87);
}
</style>
