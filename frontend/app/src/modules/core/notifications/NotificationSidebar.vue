<script setup lang="ts">
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import Notification from '@/modules/core/notifications/Notification.vue';
import PendingTasks from '@/modules/core/notifications/PendingTasks.vue';
import { TAB_ORDER, useNotificationSidebar } from '@/modules/core/notifications/use-notification-sidebar';
import LazyLoader from '@/modules/shell/components/LazyLoader.vue';

const display = defineModel<boolean>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const contentWrapper = useTemplateRef<HTMLDivElement>('contentWrapper');
const { y } = useScroll(contentWrapper);

const { visible: dialogVisible } = storeToRefs(useConfirmStore());

const [DefineNoMessages, ReuseNoMessages] = createReusableTemplate();

const {
  allNotifications,
  close,
  hasRunningTasks,
  initialAppear,
  messageOverflow,
  modelPendingTasksExpanded,
  modelSelectedTab,
  remove,
  selectedNotifications,
  showConfirmation,
  silent,
  tabCategoriesLabel,
  toggleSilentMode,
} = useNotificationSidebar({ display, scrollY: y });
</script>

<template>
  <RuiNavigationDrawer
    v-model="display"
    width="400px"
    position="right"
    temporary
    :stateless="dialogVisible"
  >
    <DefineNoMessages>
      <div class="flex flex-col items-center justify-center flex-1">
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
        <div class="flex items-center">
          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                variant="text"
                icon
                :color="silent ? 'primary' : undefined"
                data-testid="silent-notifications-toggle"
                @click="toggleSilentMode()"
              >
                <RuiIcon :name="silent ? 'lu-bell-off' : 'lu-bell'" />
              </RuiButton>
            </template>
            {{ silent ? t('notification_sidebar.silent.on') : t('notification_sidebar.silent.off') }}
          </RuiTooltip>
          <RuiButton
            variant="text"
            icon
            data-testid="close-notifications"
            @click="close()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </div>

      <ReuseNoMessages v-if="!hasRunningTasks && allNotifications.length === 0" />
      <div
        v-else
        class="flex flex-col h-[calc(100%-133px)]"
      >
        <PendingTasks v-model="modelPendingTasksExpanded" />
        <div class="border-b border-default mx-4">
          <RuiTabs
            v-model="modelSelectedTab"
            color="primary"
          >
            <RuiTab
              v-for="item in TAB_ORDER"
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
          class="ps-3.5 pe-2 mt-2 flex flex-col gap-2 !overflow-y-auto"
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
          data-testid="clear-notifications"
          @click="showConfirmation()"
        >
          {{ t('notification_sidebar.clear_tooltip') }}
        </RuiButton>
        <RouterLink :to="{ name: '/calendar/' }">
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
