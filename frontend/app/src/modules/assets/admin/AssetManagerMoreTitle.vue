<script setup lang="ts">
import { type AssetManagerMoreTool, useAssetManagerMore } from '@/modules/assets/admin/use-asset-manager-more';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const open = ref<boolean>(false);

const { current, tools } = useAssetManagerMore();

async function pick(tool: AssetManagerMoreTool): Promise<void> {
  set(open, false);
  if (tool.path !== get(current)?.path)
    await router.push(tool.path);
}
</script>

<template>
  <nav
    class="flex items-center text-sm font-medium"
    :aria-label="t('navigation_menu.manage_assets_sub.more')"
  >
    <span class="text-rui-text-secondary">{{ t('navigation_menu.manage_assets') }}</span>
    <RuiIcon
      name="lu-chevron-right"
      size="16"
      class="mx-2 text-rui-text-secondary"
    />
    <RouterLink
      to="/asset-manager/more"
      class="text-rui-text-secondary hover:text-rui-text transition-colors"
      data-testid="asset-manager-more-overview-link"
    >
      {{ t('navigation_menu.manage_assets_sub.more') }}
    </RouterLink>
    <RuiIcon
      name="lu-chevron-right"
      size="16"
      class="mx-2 text-rui-text-secondary"
    />
    <RuiMenu
      v-model="open"
      :options="{ placement: 'bottom-start' }"
    >
      <template #activator="{ attrs }">
        <button
          type="button"
          class="flex items-center gap-2 -mx-2 px-2 h-8 rounded-rui-control text-rui-text hover:bg-rui-hover transition-colors"
          :aria-label="t('asset_management.more.switch_tool')"
          data-testid="asset-manager-more-switch"
          v-bind="attrs"
        >
          <RuiIcon
            v-if="current"
            :name="current.icon"
            size="16"
            class="text-rui-text-secondary"
          />
          {{ current?.text }}
          <RuiIcon
            name="lu-chevron-down"
            size="16"
            class="text-rui-text-secondary"
          />
        </button>
      </template>
      <div class="w-72 p-1 flex flex-col gap-0.5">
        <button
          v-for="tool in tools"
          :key="tool.path"
          type="button"
          class="flex items-center gap-3 px-2 h-9 rounded-rui-control text-sm text-left hover:bg-rui-hover transition-colors"
          :class="{ 'font-medium': tool.path === current?.path }"
          :aria-current="tool.path === current?.path ? 'page' : undefined"
          data-testid="asset-manager-more-option"
          :data-path="tool.path"
          @click="pick(tool)"
        >
          <RuiIcon
            :name="tool.icon"
            size="16"
            class="text-rui-text-secondary shrink-0"
          />
          <span class="flex-1">{{ tool.text }}</span>
          <RuiIcon
            v-if="tool.path === current?.path"
            name="lu-check"
            size="16"
            class="text-rui-primary"
          />
        </button>
      </div>
    </RuiMenu>
  </nav>
</template>
