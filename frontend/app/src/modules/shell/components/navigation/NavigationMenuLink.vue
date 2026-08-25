<script setup lang="ts">
import type { MenuNavItem } from '@/modules/shell/layout/use-navigation-menu';
import NavigationMenuItem from '@/modules/shell/components/navigation/NavigationMenuItem.vue';

const { item, mini = false, subMenu = false } = defineProps<{
  item: MenuNavItem;
  mini?: boolean;
  subMenu?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();

const active = computed<boolean>(() => route.path.startsWith(item.path));
</script>

<template>
  <RouterLink
    :to="item.path"
    custom
  >
    <template #default="{ isActive, href, navigate }">
      <!--
        `custom` leaves the anchor's default action in place, so without this handler the
        click is a plain hash navigation racing the router's own. The browser's entry
        carries no state, and vue-router replaces such an entry with the position it was
        already on, leaving two entries sharing one position.
      -->
      <a
        :href="href"
        @click="navigate($event)"
      >
        <NavigationMenuItem
          data-testid="navigation"
          :data-key="item.testId"
          :mini="mini"
          :text="t(item.labelKey)"
          :icon="item.icon"
          :active="isActive || active"
          :sub-menu="subMenu"
        />
      </a>
    </template>
  </RouterLink>
</template>
