<script setup lang="ts">
defineProps<{ visible: boolean }>();

const emit = defineEmits(['close']);

const { t } = useI18n();

const css = useCssModule();

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
      title: t('notification_sidebar.confirmation.title'),
      message: t('notification_sidebar.confirmation.message'),
      type: 'info'
    },
    clear
  );
};

const { mobile } = useDisplay();
const { hasRunningTasks } = storeToRefs(useTaskStore());

const itemHeight = 172;
const margin = 8;

const { list, containerProps, wrapperProps } = useVirtualList(notifications, {
  itemHeight
});

const notificationStyle = {
  height: `${itemHeight - margin}px`,
  marginTop: `${margin}px`
};
</script>

<template>
  <VNavigationDrawer
    :class="{ [css.mobile]: mobile, [css.sidebar]: true }"
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
    <div v-if="visible" class="h-full overflow-hidden">
      <div class="flex items-center p-2 gap-1">
        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton variant="text" icon class="!p-2" @click="close()">
              <RuiIcon name="arrow-right-s-line" size="20" />
            </RuiButton>
          </template>
          <span>{{ t('notification_sidebar.close_tooltip') }}</span>
        </RuiTooltip>
        <div
          class="flex-1 text-uppercase text--secondary text-caption font-medium"
        >
          {{ t('notification_sidebar.title') }}
        </div>
        <RuiButton
          variant="text"
          class="text-caption text-lowercase"
          color="secondary"
          :disabled="notifications.length === 0"
          @click="showConfirmation()"
        >
          {{ t('notification_sidebar.clear_tooltip') }}
        </RuiButton>
      </div>
      <div
        v-if="!hasRunningTasks && notifications.length === 0"
        :class="css['no-messages']"
      >
        <RuiIcon size="64px" color="primary" name="information-line" />
        <div class="text-rui-text text-lg mt-2">
          {{ t('notification_sidebar.no_messages') }}
        </div>
      </div>
      <div v-else :class="css.messages">
        <PendingTasks />
        <div
          v-if="notifications.length > 0"
          :class="css.content"
          class="ps-3.5 !overflow-y-scroll"
          v-bind="containerProps"
          @scroll="containerProps.onScroll"
        >
          <div v-bind="wrapperProps">
            <Notification
              v-for="item in list"
              :key="item.index"
              :notification="item.data"
              :style="notificationStyle"
              @dismiss="remove($event)"
            />
          </div>
        </div>
      </div>
    </div>
  </VNavigationDrawer>
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

.messages {
  height: calc(100% - 50px);
}

.content {
  height: calc(100% - 74px);
}
</style>
