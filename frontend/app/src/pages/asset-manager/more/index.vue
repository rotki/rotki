<script setup lang="ts">
import { useAssetManagerMore } from '@/modules/assets/admin/use-asset-manager-more';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const { tools } = useAssetManagerMore();
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.manage_assets'), t('navigation_menu.manage_assets_sub.more')]"
    child
    data-testid="asset-manager-more-overview"
  >
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <RouterLink
        v-for="tool in tools"
        :key="tool.path"
        :to="tool.path"
        class="group flex items-start gap-4 p-4 rounded-rui-card border border-rui-divider bg-rui-surface hover:border-rui-primary-border hover:bg-rui-primary-subtle transition-colors"
        data-testid="asset-manager-more-card"
        :data-path="tool.path"
      >
        <div class="shrink-0 size-10 flex items-center justify-center rounded-rui-control bg-rui-primary/10 text-rui-primary">
          <RuiIcon
            :name="tool.icon"
            size="20"
          />
        </div>
        <div class="flex flex-col gap-0.5 min-w-0 flex-1">
          <span class="text-base font-medium text-rui-text">{{ tool.text }}</span>
          <span class="text-sm text-rui-text-secondary">{{ tool.description }}</span>
        </div>
        <RuiIcon
          name="lu-chevron-right"
          size="16"
          class="self-center shrink-0 text-rui-text-secondary group-hover:text-rui-primary transition-colors"
        />
      </RouterLink>
    </div>
  </TablePageLayout>
</template>
