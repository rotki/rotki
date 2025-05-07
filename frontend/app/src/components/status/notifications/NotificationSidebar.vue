<script setup lang="ts">
import LazyLoader from '@/components/helper/LazyLoader.vue';
import Notification from '@/components/status/notifications/Notification.vue';
import PendingTasks from '@/components/status/notifications/PendingTasks.vue';
import { Routes } from '@/router/routes';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { type NotificationData, Priority, Severity } from '@rotki/common';

const display = defineModel<boolean>({ required: true });

enum TabCategory {
  VIEW_ALL = 'view_all',
  NEEDS_ACTION = 'needs_action',
  REMINDER = 'reminder',
  ERROR = 'error',
}

const contentWrapper = ref();
const selectedTab = ref<TabCategory>(TabCategory.VIEW_ALL);
const initialAppear = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

const confirmStore = useConfirmStore();
const { visible: dialogVisible } = storeToRefs(confirmStore);
const { show } = confirmStore;

const notificationStore = useNotificationsStore();
const { messageOverflow, prioritized: allNotifications } = storeToRefs(notificationStore);
const { remove } = notificationStore;
const { hasRunningTasks } = storeToRefs(useTaskStore());
const [DefineNoMessages, ReuseNoMessages] = createReusableTemplate();
const { y } = useScroll(contentWrapper);

const tabCategoriesLabel = computed(() => ({
  [TabCategory.ERROR]: t('notification_sidebar.tabs.error'),
  [TabCategory.NEEDS_ACTION]: t('notification_sidebar.tabs.needs_action'),
  [TabCategory.REMINDER]: t('notification_sidebar.tabs.reminder'),
  [TabCategory.VIEW_ALL]: t('notification_sidebar.tabs.view_all'),
}));

const selectedNotifications = computed(() => {
  const all = get(allNotifications);
  const tab = get(selectedTab);
  const filters: Partial<Record<TabCategory, (item: NotificationData) => boolean>> = {
    [TabCategory.ERROR]: (item: NotificationData) => item.severity === Severity.ERROR,
    [TabCategory.NEEDS_ACTION]: (item: NotificationData) => item.priority === Priority.ACTION,
    [TabCategory.REMINDER]: (item: NotificationData) => item.severity === Severity.REMINDER,
  };

  const filterBy = filters[tab];
  if (filterBy) {
    return all.filter(filterBy);
  }

  return all;
});

function close() {
  set(display, false);
}

function clear() {
  notificationStore.$reset();
  close();
}

function showConfirmation() {
  show({
    message: t('notification_sidebar.confirmation.message'),
    title: t('notification_sidebar.confirmation.title'),
    type: 'info',
  }, clear);
}

watch(
  [y, selectedTab, selectedNotifications],
  ([currentY, currSelectedTab, currNotifications], [_, prevSelectedTab, prevNotifications]) => {
    if (currSelectedTab !== prevSelectedTab || (prevNotifications.length === 0 && currNotifications.length > 0)) {
      set(initialAppear, false);
      nextTick(() => {
        set(initialAppear, true);
      });
    }
    else {
      set(initialAppear, currentY <= 0);
    }
  },
);
</script>

<template>
  <RuiNavigationDrawer
    v-model="display"
    :content-class="$style.sidebar"
    width="400px"
    position="right"
    temporary
    :stateless="dialogVisible"
  >
    <DefineNoMessages>
      <div :class="$style['no-messages']">
        <RuiIcon
          size="64px"
          color="primary"
          name="lu-info"
        />
        <div class="text-rui-text text-lg mt-2">
          {{ t('notification_sidebar.no_messages') }}
        </div>
      </div>
    </DefineNoMessages>
    <div class="h-full overflow-hidden flex flex-col">
      <div class="flex justify-between items-center p-2 pl-4">
        <div class="text-h6">
          {{ t('notification_sidebar.title') }}
        </div>
        <RuiButton
          variant="text"
          icon
          @click="close()"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </div>

      <ReuseNoMessages v-if="!hasRunningTasks && allNotifications.length === 0" />
      <div
        v-else
        :class="$style.messages"
      >
        <PendingTasks />
        <div class="border-b border-default mx-4">
          <RuiTabs
            v-model="selectedTab"
            color="primary"
          >
            <RuiTab
              v-for="item in Object.values(TabCategory)"
              :key="item"
              size="sm"
              class="!min-w-0"
              :value="item"
            >
              {{ tabCategoriesLabel[item] }}
            </RuiTab>
          </RuiTabs>
        </div>
        <div
          v-if="selectedNotifications.length > 0"
          ref="contentWrapper"
          :class="$style.content"
        >
          <LazyLoader
            v-for="item in selectedNotifications"
            :key="item.id"
            :initial-appear="initialAppear"
            min-height="120px"
            class="grow-0 shrink-0"
          >
            <Notification
              :notification="item"
              @dismiss="remove($event)"
            />
          </LazyLoader>
          <div
            v-if="messageOverflow"
            class="flex bg-rui-warning/[.1] rounded-md border p-2 gap-4"
          >
            <div class="flex flex-col justify-center items-center">
              <div class="rounded-full p-2 bg-rui-warning">
                <RuiIcon
                  size="20"
                  class="text-white"
                  name="lu-siren"
                />
              </div>
            </div>

            <div class="text-rui-text-secondary text-body-2 break-words">
              {{ t('notification_sidebar.message_overflow') }}
            </div>
          </div>
        </div>
        <ReuseNoMessages v-else />
      </div>
      <div class="p-3 flex justify-between border-t border-default mt-2">
        <RuiButton
          variant="text"
          color="primary"
          :disabled="allNotifications.length === 0"
          @click="showConfirmation()"
        >
          {{ t('notification_sidebar.clear_tooltip') }}
        </RuiButton>
        <RouterLink :to="Routes.CALENDAR">
          <RuiButton
            color="primary"
            @click="close()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-calendar-days"
                size="20"
              />
            </template>
            {{ t('notification_sidebar.view_calendar') }}
          </RuiButton>
        </RouterLink>
      </div>
    </div>
  </RuiNavigationDrawer>
</template>

<style module lang="scss">
.no-messages {
  @apply flex flex-col items-center justify-center flex-1;
}

.messages {
  @apply flex flex-col;
  height: calc(100% - 133px);
}

.content {
  @apply ps-3.5 pe-2 mt-2 flex flex-col gap-2;
  @apply overflow-y-auto #{!important};
}
</style>
