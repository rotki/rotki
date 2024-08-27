<script setup lang="ts">
import { Priority, Severity } from '@rotki/common';
import { Routes } from '@/router/routes';

const display = defineModel<boolean>({ required: true });

const { t } = useI18n();

const confirmStore = useConfirmStore();
const { visible: dialogVisible } = storeToRefs(confirmStore);
const { show } = confirmStore;

const notificationStore = useNotificationsStore();
const { prioritized: allNotifications } = storeToRefs(notificationStore);
const { remove } = notificationStore;

function close() {
  set(display, false);
}

function clear() {
  notificationStore.$reset();
  close();
}

function showConfirmation() {
  show(
    {
      title: t('notification_sidebar.confirmation.title'),
      message: t('notification_sidebar.confirmation.message'),
      type: 'info',
    },
    clear,
  );
}

const { hasRunningTasks } = storeToRefs(useTaskStore());

enum TabCategory {
  VIEW_ALL = 'view_all',
  NEEDS_ACTION = 'needs_action',
  REMINDER = 'reminder',
  ERROR = 'error',
}

const tabCategoriesLabel = computed(() => ({
  [TabCategory.VIEW_ALL]: t('notification_sidebar.tabs.view_all'),
  [TabCategory.NEEDS_ACTION]: t('notification_sidebar.tabs.needs_action'),
  [TabCategory.REMINDER]: t('notification_sidebar.tabs.reminder'),
  [TabCategory.ERROR]: t('notification_sidebar.tabs.error'),
}));

const selectedTab = ref<TabCategory>(TabCategory.VIEW_ALL);

const selectedNotifications = computed(() => {
  const all = get(allNotifications);
  const tab = get(selectedTab);

  if (tab === TabCategory.NEEDS_ACTION)
    return all.filter(item => item.priority === Priority.ACTION);

  if (tab === TabCategory.ERROR)
    return all.filter(item => item.severity === Severity.ERROR);

  if (tab === TabCategory.REMINDER)
    return all.filter(item => item.severity === Severity.REMINDER);

  return all;
});

const [DefineNoMessages, ReuseNoMessages] = createReusableTemplate();

const contentWrapper = ref();
const { y } = useScroll(contentWrapper);

const initialAppear = ref<boolean>(false);

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
      if (currentY > 0)
        set(initialAppear, false);
      else set(initialAppear, true);
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
          name="information-line"
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
          <RuiIcon name="close-line" />
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
                name="calendar-event-line"
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
