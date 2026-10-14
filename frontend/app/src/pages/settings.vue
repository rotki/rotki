<script setup lang="ts">
import { msg } from '@/message-key';
import { type TabContent, tabKey } from '@/modules/core/common/tabs';
import SettingsSearch from '@/modules/settings/SettingsSearch.vue';
import TabNavigation from '@/modules/shell/components/TabNavigation.vue';
import { useNavTabs } from '@/modules/shell/layout/use-nav-tabs';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.settings'), icon: 'lu-settings', searchable: false },
    scrollsItself: true,
  },
  redirect: { name: '/settings/account/' },
});

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();

const switcherOpen = ref<boolean>(false);

const tabs = useNavTabs([
  '/settings/account/',
  '/settings/general/',
  '/settings/database/',
  '/settings/accounting/',
  '/settings/chains/',
  '/settings/oracle/',
  '/settings/rpc/',
  '/settings/modules/',
  '/settings/mcp/',
  '/settings/interface/',
]);

/** The open category, named in the breadcrumb; on a narrow screen it is also the way to switch. */
const current = computed<TabContent | undefined>(() => get(tabs).find(tab => isWithin(route.path, tab.route.toString())));

/** Whether `path` is `base` or below it, compared by whole segments, so /settings/account does not claim /settings/accounting. */
function isWithin(path: string, base: string): boolean {
  const withSlash = (value: string): string => (value.endsWith('/') ? value : `${value}/`);
  return withSlash(path).startsWith(withSlash(base));
}
</script>

<template>
  <div class="container lg:px-8 flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-x-8 gap-y-2 min-h-9">
      <nav
        class="flex items-center text-sm font-medium"
        :aria-label="t('navigation_menu.settings')"
      >
        <span class="text-rui-text-secondary">{{ t('navigation_menu.settings') }}</span>
        <RuiIcon
          name="lu-chevron-right"
          size="16"
          class="mx-2 text-rui-text-secondary"
        />
        <span class="hidden md:inline text-rui-text">{{ current?.text }}</span>
        <RuiMenu
          v-model="switcherOpen"
          class="md:hidden"
          :options="{ placement: 'bottom-start' }"
        >
          <template #activator="{ attrs }">
            <button
              type="button"
              class="flex items-center gap-2 -mx-2 px-2 h-8 rounded-rui-control text-rui-text hover:bg-rui-hover transition-colors"
              data-testid="settings-section-switch"
              v-bind="attrs"
            >
              {{ current?.text }}
              <RuiIcon
                name="lu-chevron-down"
                size="16"
                class="text-rui-text-secondary"
              />
            </button>
          </template>
          <div class="w-60 p-1 flex flex-col">
            <RouterLink
              v-for="tab in tabs"
              :key="tab.route.toString()"
              :to="tab.route"
              class="flex items-center gap-3 px-3 h-9 rounded-rui-control text-sm text-rui-text hover:bg-rui-hover transition-colors"
              :class="{ 'font-medium bg-rui-hover': tab === current }"
              :aria-current="tab === current ? 'page' : undefined"
              data-testid="settings-section-link"
              :data-key="tabKey(tab.route.toString())"
              @click="switcherOpen = false"
            >
              <RuiIcon
                :name="tab.icon"
                size="16"
                class="text-rui-text-secondary"
              />
              {{ tab.text }}
            </RouterLink>
          </div>
        </RuiMenu>
      </nav>

      <SettingsSearch />
    </div>
    <TabNavigation
      :tabs="tabs"
      plain
      child
      hide-router-view
      class="settings hidden md:block"
    />
    <RouterView />
  </div>
</template>
