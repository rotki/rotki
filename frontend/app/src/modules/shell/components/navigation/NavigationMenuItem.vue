<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { Component } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import AppImage from '@/modules/shell/components/AppImage.vue';

const { mini = false, icon, text, image = '', iconComponent, active = false, subMenu = false, parent = false, to } = defineProps<{
  mini?: boolean;
  icon?: RuiIcons;
  text: string;
  image?: string;
  iconComponent?: Component;
  active?: boolean;
  subMenu?: boolean;
  parent?: boolean;
  to?: RouteLocationRaw;
}>();

defineSlots<{
  default: () => any;
}>();

const router = useRouter();

const [DefineImage, ReuseImage] = createReusableTemplate();

const outer = useTemplateRef<HTMLDivElement>('outer');
const inner = useTemplateRef<HTMLDivElement>('inner');
const { height: innerHeight } = useElementSize(inner);
const subMenuExpanded = ref<boolean>(false);

const submenuWrapperStyle = computed(() => get(subMenuExpanded) ? { height: `${get(innerHeight)}px` } : {});

function toggleExpand(): void {
  const newState = !get(subMenuExpanded);
  set(subMenuExpanded, newState);

  if (newState) {
    setTimeout(() => {
      get(outer)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 150);
  }
}

function onBodyClick(): void {
  if (!parent)
    return;

  if (to && !get(subMenuExpanded)) {
    router.push(to);
    toggleExpand();
  }
  else {
    toggleExpand();
  }
}

onMounted(() => {
  if (parent && active)
    set(subMenuExpanded, true);
});
</script>

<template>
  <div ref="outer">
    <div
      class="flex items-center grow gap-3 rounded-rui-control px-3 text-sm transition-colors cursor-pointer"
      :class="{
        'h-10': !subMenu,
        'h-9': subMenu,
        'bg-rui-primary-fill text-rui-primary-foreground font-medium': active && !parent,
        'text-rui-primary font-medium hover:bg-rui-hover': active && parent,
        'text-rui-text hover:bg-rui-hover': !active,
        'pl-11 pr-0': subMenu && !mini,
        'px-0 justify-center': mini,
        'pl-3': mini && subMenu,
      }"
      data-testid="navigation-item-body"
      @click="onBodyClick()"
    >
      <DefineImage>
        <div
          class="flex shrink-0"
          :class="active ? (parent ? 'text-rui-primary' : 'text-rui-primary-foreground') : 'text-rui-text-secondary'"
        >
          <AppImage
            v-if="image"
            fit="contain"
            :width="subMenu ? '18px' : '20px'"
            :src="image"
            :class="active ? 'opacity-100 brightness-0 invert' : 'opacity-70 brightness-0 dark:opacity-100 dark:invert'"
          />
          <Component
            :is="iconComponent"
            v-else-if="iconComponent"
            :active="active"
          />
          <RuiIcon
            v-else-if="icon"
            :name="icon"
            :size="subMenu ? 18 : 20"
          />
        </div>
      </DefineImage>
      <RuiTooltip
        v-if="mini"
        :options="{ placement: 'right' }"
        :open-delay="400"
      >
        <template #activator>
          <ReuseImage />
        </template>
        {{ text }}
      </RuiTooltip>
      <template v-else>
        <ReuseImage />
        <div class="flex grow min-w-0 truncate">
          {{ text }}
        </div>
      </template>
      <div
        v-if="parent && !mini"
        class="p-1 -mr-1 rounded-full hover:bg-rui-hover"
        :class="active ? 'text-rui-primary' : 'text-rui-text-secondary'"
        data-testid="navigation-item-chevron"
        @click.stop="toggleExpand()"
      >
        <RuiIcon
          name="lu-chevron-down"
          size="16"
          class="transition-transform"
          :class="{ 'rotate-180': subMenuExpanded }"
        />
      </div>
    </div>
    <div
      v-if="parent"
      class="transition-all h-0 overflow-hidden"
      :style="submenuWrapperStyle"
      data-testid="submenu-wrapper"
      :data-expanded="subMenuExpanded"
    >
      <div ref="inner">
        <slot />
      </div>
    </div>
  </div>
</template>
