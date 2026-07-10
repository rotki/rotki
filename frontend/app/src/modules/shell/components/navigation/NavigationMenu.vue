<script setup lang="ts">
import NavigationMenuGroup from '@/modules/shell/components/navigation/NavigationMenuGroup.vue';
import NavigationMenuLink from '@/modules/shell/components/navigation/NavigationMenuLink.vue';
import { useNavigationMenu } from '@/modules/shell/layout/use-navigation-menu';

const { isMini = false } = defineProps<{
  isMini?: boolean;
}>();

const { menuItems } = useNavigationMenu();
</script>

<template>
  <div
    class="p-3"
    :class="{ '!p-0': isMini }"
  >
    <template
      v-for="(navItem, i) in menuItems"
      :key="i"
    >
      <RuiDivider
        v-if="navItem.type === 'divider'"
        class="my-2"
      />
      <NavigationMenuGroup
        v-else-if="navItem.type === 'group'"
        :group="navItem"
        :mini="isMini"
      />
      <NavigationMenuLink
        v-else
        :item="navItem"
        :mini="isMini"
      />
    </template>
  </div>
</template>
