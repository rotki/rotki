<template>
  <v-navigation-drawer
    :class="{ [$style.mobile]: isMobile, [$style.sidebar]: true }"
    width="400px"
    absolute
    clipped
    :value="visible"
    right
    temporary
    hide-overlay
    @input="input($event)"
  >
    <v-row align="center" no-gutters class="pl-2 pr-2 pt-1 pb-2">
      <v-col cols="auto">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn text icon v-on="on" @click="close()">
              <v-icon>mdi-chevron-right</v-icon>
            </v-btn>
          </template>
          <span>{{ $t('notification_sidebar.close_tooltip') }}</span>
        </v-tooltip>
      </v-col>
      <v-col>
        <span
          class="
            text-uppercase text--secondary text-caption
            font-weight-medium
            pl-1
          "
        >
          {{ $t('notification_sidebar.title') }}
        </span>
      </v-col>
      <v-col cols="auto">
        <v-btn
          text
          class="text-caption text-lowercase"
          color="accent"
          :disabled="notifications.length === 0"
          @click="confirmClear = true"
        >
          {{ $t('notification_sidebar.clear_tooltip') }}
        </v-btn>
      </v-col>
    </v-row>
    <div
      v-if="!hasRunningTasks && notifications.length === 0"
      :class="$style['no-messages']"
    >
      <v-icon size="64px" color="primary">mdi-information</v-icon>
      <div :class="$style.label">
        {{ $t('notification_sidebar.no_messages') }}
      </div>
    </div>
    <div v-else :class="$style.messages">
      <pending-tasks />
      <div v-if="notifications.length > 0" class="pl-2">
        <notification
          v-for="notification in notifications"
          :key="notification.id"
          class="mb-2"
          :notification="notification"
          @dismiss="remove($event)"
        />
      </div>
    </div>
    <confirm-dialog
      :display="confirmClear"
      :title="$t('notification_sidebar.confirmation.title')"
      :message="$t('notification_sidebar.confirmation.message')"
      @cancel="confirmClear = false"
      @confirm="clear()"
    />
  </v-navigation-drawer>
</template>

<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import orderBy from 'lodash/orderBy';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import Notification from '@/components/status/notifications/Notification.vue';
import PendingTasks from '@/components/status/notifications/PendingTasks.vue';
import { setupThemeCheck } from '@/composables/common';
import { setupNotifications } from '@/composables/notifications';
import { setupTaskStatus } from '@/composables/tasks';

const NotificationSidebar = defineComponent({
  components: { PendingTasks, Notification, ConfirmDialog },
  props: {
    visible: { required: true, type: Boolean }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const confirmClear = ref(false);

    const { reset, remove, data } = setupNotifications();
    const close = () => {
      emit('close');
    };

    const input = (visible: boolean) => {
      if (visible) {
        return;
      }
      close();
    };

    const clear = () => {
      confirmClear.value = false;
      reset();
      close();
    };

    const notifications = computed(() => {
      return orderBy(data.value, 'id', 'desc');
    });

    const { isMobile } = setupThemeCheck();
    const { hasRunningTasks } = setupTaskStatus();

    return {
      isMobile,
      notifications,
      hasRunningTasks,
      confirmClear,
      input,
      close,
      clear,
      remove
    };
  }
});
export default NotificationSidebar;
</script>

<style module lang="scss">
.sidebar {
  top: 64px !important;
  box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);
  padding-top: 0 !important;
  border-top: var(--v-rotki-light-grey-darken1) solid thin;

  :global {
    .v-badge {
      &__badge {
        top: 0 !important;
        right: 0 !important;
      }
    }

    .v-list-item {
      &__action-text {
        margin-right: -8px;
        margin-top: -8px;
      }
    }
  }

  @media only screen and (max-width: 960px) {
    top: 56px !important;
  }
}

.mobile {
  top: 56px !important;
  padding-top: 0 !important;
}

.no-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100% - 64px);
}

.label {
  font-size: 22px;
  margin-top: 22px;
  font-weight: 300;
  color: rgb(0, 0, 0, 0.6);
}

.messages {
  height: calc(100% - 64px);
  overflow-y: scroll !important;
}
</style>
