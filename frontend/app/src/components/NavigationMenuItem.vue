<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import type { RuiIcons } from '@rotki/ui-library';
import type { Component } from 'vue';

withDefaults(
  defineProps<{
    mini?: boolean;
    icon?: RuiIcons;
    text: string;
    image?: string;
    iconComponent?: Component;
    active?: boolean;
    subMenu?: boolean;
    parent?: boolean;
  }>(),
  {
    active: false,
    icon: undefined,
    iconComponent: undefined,
    image: '',
    mini: false,
    parent: false,
    subMenu: false,
  },
);

defineSlots<{
  default: () => any;
}>();

const [DefineImage, ReuseImage] = createReusableTemplate();

const outer = ref<HTMLDivElement>();
const inner = ref<HTMLDivElement>();
const { height: innerHeight } = useElementSize(inner);
const subMenuExpanded = ref<boolean>(false);

function expandParent() {
  if (!get(parent))
    return;

  const newState = !get(subMenuExpanded);
  set(subMenuExpanded, newState);

  if (newState) {
    setTimeout(() => {
      get(outer)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 150);
  }
}
</script>

<template>
  <div ref="outer">
    <div
      :class="[
        $style.wrapper,
        {
          [$style.active]: active,
          [$style.active__parent]: active && parent,
          [$style.mini]: mini,
          [$style.submenu]: subMenu,
        },
      ]"
      @click="expandParent()"
    >
      <DefineImage>
        <div
          :class="[
            $style.icon,
            {
              ['mr-2']: subMenu && !mini,
              ['mr-3']: !subMenu && !mini,
              ['my-2']: subMenu,
              ['my-3']: !subMenu,
            },
          ]"
        >
          <AppImage
            v-if="image"
            contain
            width="24px"
            :src="image"
            :class="$style.image"
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
        :class="$style.toggle"
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
      :class="[
        $style['submenu-wrapper'],
        {
          [`${$style.expanded} submenu-wrapper__expanded`]: subMenuExpanded,
        },
      ]"
      class="submenu-wrapper"
    >
      <div ref="inner">
        <slot />
      </div>
    </div>
  </div>
</template>

<style module lang="scss">
.wrapper {
  @apply flex items-center grow rounded px-3 py-0 text-rui-text hover:bg-rui-grey-100 transition cursor-pointer;

  .icon {
    @apply text-rui-text-secondary;

    .image {
      @apply opacity-70 brightness-0;
    }
  }

  .toggle {
    @apply text-rui-grey-500;
  }

  &.active {
    @apply bg-rui-primary font-bold text-white hover:bg-rui-primary;

    .icon {
      @apply text-white;

      .image {
        @apply opacity-100 filter brightness-0 invert;
      }
    }

    &__parent {
      @apply font-medium bg-transparent text-rui-primary hover:bg-rui-grey-100;

      .icon,
      .toggle {
        @apply text-rui-primary;
      }
    }
  }

  &.submenu {
    @apply pl-12 pr-0 text-sm;
  }

  &.mini {
    @apply px-0 flex justify-center;

    &.submenu {
      @apply pl-0;
    }
  }
}

.submenu-wrapper {
  @apply transition-all h-0 overflow-hidden;

  &.expanded {
    height: calc(v-bind(innerHeight) * 1px) !important;
  }
}

:global(.dark) {
  .wrapper {
    @apply hover:bg-rui-grey-800;

    &.active {
      @apply hover:bg-rui-primary;

      &__parent {
        @apply hover:bg-rui-grey-800;
      }
    }

    .icon {
      .image {
        @apply opacity-100 brightness-0 invert;
      }
    }
  }
}
</style>
