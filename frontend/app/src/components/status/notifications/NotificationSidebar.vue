<script setup lang="ts">
defineProps<{ visible: boolean }>();

const { t, tc } = useI18n();
const css = useCssModule();

const emit = defineEmits(['close']);
const confirmStore = useConfirmStore();
const { visible: dialogVisible } = storeToRefs(confirmStore);
const { show } = confirmStore;

const notificationStore = useNotificationsStore();
const { prioritized: notifications } = storeToRefs(notificationStore);
const { remove } = notificationStore;

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
  notificationStore.$reset();
  close();
};

const showConfirmation = () => {
  show(
    {
      title: tc('notification_sidebar.confirmation.title'),
      message: tc('notification_sidebar.confirmation.message'),
      type: 'info'
    },
    clear
  );
};

const { isMobile } = useTheme();
const { hasRunningTasks } = storeToRefs(useTaskStore());
</script>

<template>
  <v-navigation-drawer
    :class="{ [css.mobile]: isMobile, [css.sidebar]: true }"
    width="400px"
    absolute
    clipped
    :value="visible"
    :stateless="dialogVisible"
    right
    temporary
    hide-overlay
    @input="input($event)"
  >
    <div v-if="visible" :class="css.container">
      <v-row align="center" no-gutters class="pl-2 pr-2 pt-1 pb-2">
        <v-col cols="auto">
          <v-tooltip bottom>
            <template #activator="{ on }">
              <v-btn text icon v-on="on" @click="close()">
                <v-icon>mdi-chevron-right</v-icon>
              </v-btn>
            </template>
            <span>{{ t('notification_sidebar.close_tooltip') }}</span>
          </v-tooltip>
        </v-col>
        <v-col>
          <span
            class="text-uppercase text--secondary text-caption font-weight-medium pl-1"
          >
            {{ t('notification_sidebar.title') }}
          </span>
        </v-col>
        <v-col cols="auto">
          <v-btn
            text
            class="text-caption text-lowercase"
            color="accent"
            :disabled="notifications.length === 0"
            @click="showConfirmation()"
          >
            {{ t('notification_sidebar.clear_tooltip') }}
          </v-btn>
        </v-col>
      </v-row>
      <div
        v-if="!hasRunningTasks && notifications.length === 0"
        :class="$style['no-messages']"
      >
        <v-icon size="64px" color="primary">mdi-information</v-icon>
        <div :class="css.label">
          {{ t('notification_sidebar.no_messages') }}
        </div>
      </div>
      <div v-else :class="css.messages">
        <pending-tasks />
        <div v-if="notifications.length > 0" class="pl-2" :class="css.content">
          <v-virtual-scroll :items="notifications" item-height="172px">
            <template #default="{ item }">
              <notification :notification="item" @dismiss="remove($event)" />
            </template>
          </v-virtual-scroll>
        </div>
      </div>
    </div>
  </v-navigation-drawer>
</template>

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

.container {
  height: 100%;
}

.messages {
  height: calc(100% - 50px);
  padding-right: 0.5rem;
}

.content {
  height: calc(100% - 64px);
}
</style>
