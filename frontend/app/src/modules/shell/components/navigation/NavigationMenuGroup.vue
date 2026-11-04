<script setup lang="ts">
import type { MenuNavGroup } from '@/modules/shell/layout/use-navigation-menu';
import NavigationMenuItem from '@/modules/shell/components/navigation/NavigationMenuItem.vue';
import NavigationMenuLink from '@/modules/shell/components/navigation/NavigationMenuLink.vue';

const { group, mini = false } = defineProps<{
  group: MenuNavGroup;
  mini?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RouterLink
    :to="group.path"
    custom
  >
    <template #default="{ isActive }">
      <NavigationMenuItem
        data-testid="navigation"
        :data-key="group.testId"
        :mini="mini"
        :text="t(group.labelKey)"
        :icon="group.icon"
        :active="isActive"
        :to="group.items[0]?.path"
        parent
      >
        <div :class="{ 'bg-rui-surface-muted rounded-rui-control': mini }">
          <template
            v-for="(child, i) in group.items"
            :key="i"
          >
            <RuiDivider
              v-if="mini && child.headingKey && i > 0"
              class="my-1"
              data-testid="navigation-heading-divider"
            />
            <div
              v-else-if="!mini && child.headingKey"
              class="pl-11 pr-3 pb-1 text-xs font-medium uppercase tracking-wider text-rui-text-secondary"
              :class="i > 0 ? 'pt-3' : 'pt-2'"
              data-testid="navigation-heading"
            >
              {{ t(child.headingKey) }}
            </div>
            <NavigationMenuLink
              :item="child"
              :mini="mini"
              sub-menu
            />
          </template>
        </div>
      </NavigationMenuItem>
    </template>
  </RouterLink>
</template>
