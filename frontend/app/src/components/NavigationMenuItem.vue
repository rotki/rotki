<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { Component } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import AppImage from '@/components/common/AppImage.vue';

const props = withDefaults(
  defineProps<{
    mini?: boolean;
    icon?: RuiIcons;
    text: string;
    image?: string;
    iconComponent?: Component;
    active?: boolean;
    subMenu?: boolean;
    parent?: boolean;
    to?: RouteLocationRaw;
  }>(),
  {
    active: false,
    icon: undefined,
    iconComponent: undefined,
    image: '',
    mini: false,
    parent: false,
    subMenu: false,
    to: undefined,
  },
);

defineSlots<{
  default: () => any;
}>();

const router = useRouter();

const [DefineImage, ReuseImage] = createReusableTemplate();

const outer = ref<HTMLDivElement>();
const inner = ref<HTMLDivElement>();
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
  if (!props.parent)
    return;

  if (props.to && !get(subMenuExpanded)) {
    router.push(props.to);
    toggleExpand();
  }
  else {
    toggleExpand();
  }
}
</script>

<template>
  <div ref="outer">
    <div
      class="flex items-center grow rounded px-3 py-0 text-rui-text hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800 transition cursor-pointer"
      :class="{
        'bg-rui-primary font-bold text-white hover:!bg-rui-primary': active && !parent,
        'font-medium bg-transparent !text-rui-primary': active && parent,
        'pl-12 pr-0 text-sm': subMenu && !mini,
        'px-0 justify-center': mini,
        'pl-0': mini && subMenu,
      }"
      @click="onBodyClick()"
    >
      <DefineImage>
        <div
          :class="[
            mini ? '' : (subMenu ? 'mr-2' : 'mr-3'),
            subMenu ? 'my-2' : 'my-3',
            active ? (parent ? 'text-rui-primary' : 'text-white') : 'text-rui-text-secondary',
          ]"
        >
          <AppImage
            v-if="image"
            contain
            width="24px"
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
          />
        </div>
      </DefineImage>
      <RuiTooltip
        v-if="mini"
        :popper="{ placement: 'right' }"
        :open-delay="400"
      >
        <template #activator>
          <ReuseImage />
        </template>
        {{ text }}
      </RuiTooltip>
      <template v-else>
        <ReuseImage />
        <div class="flex grow py-0 navigation-menu-item__text">
          {{ text }}
        </div>
      </template>
      <div
        v-if="parent && !mini"
        class="p-1 -mr-1 rounded-full hover:bg-black/10 dark:hover:bg-white/10"
        :class="active ? 'text-rui-primary' : 'text-rui-grey-500'"
        @click.stop="toggleExpand()"
      >
        <RuiIcon
          name="lu-chevron-down"
          class="transition-all transform"
          :class="{ 'rotate-180': subMenuExpanded }"
        />
      </div>
    </div>
    <div
      v-if="parent"
      class="transition-all h-0 overflow-hidden"
      :style="submenuWrapperStyle"
      data-cy="submenu-wrapper"
      :data-expanded="subMenuExpanded"
    >
      <div ref="inner">
        <slot />
      </div>
    </div>
  </div>
</template>
