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
        <div :class="{ 'bg-rui-grey-200 dark:bg-rui-grey-800 rounded-md': mini }">
          <NavigationMenuLink
            v-for="(child, i) in group.items"
            :key="i"
            :item="child"
            :mini="mini"
            sub-menu
          />
        </div>
      </NavigationMenuItem>
    </template>
  </RouterLink>
</template>
