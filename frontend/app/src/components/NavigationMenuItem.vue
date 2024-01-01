<script setup lang="ts">
import { type VueConstructor } from 'vue';

withDefaults(
  defineProps<{
    mini?: boolean;
    icon?: string;
    text: string;
    image?: string;
    iconComponent?: VueConstructor | null;
    active?: boolean;
    subMenu?: boolean;
    parent?: boolean;
  }>(),
  {
    mini: false,
    icon: '',
    image: '',
    iconComponent: null,
    active: false,
    subMenu: false,
    parent: false
  }
);

const [DefineImage, ReuseImage] = createReusableTemplate();

const inner = ref<HTMLDivElement>();
const { height: innerHeight } = useElementSize(inner);
const subMenuExpanded: Ref<boolean> = ref(false);

const expandParent = () => {
  if (!get(parent)) {
    return;
  }
  set(subMenuExpanded, !get(subMenuExpanded));
};

const css = useCssModule();
</script>

<template>
  <div>
    <div
      :class="[
        css.wrapper,
        { [css.active]: active, [css.mini]: mini, [css.submenu]: subMenu }
      ]"
      @click="expandParent()"
    >
      <DefineImage>
        <div
          :class="[
            css.icon,
            {
              ['mr-2']: subMenu && !mini,
              ['mr-3']: !subMenu && !mini,
              ['my-2']: subMenu,
              ['my-3']: !subMenu
            }
          ]"
        >
          <AppImage
            v-if="image"
            contain
            width="24px"
            :src="image"
            :class="css.image"
          />
          <Component
            :is="iconComponent"
            v-else-if="iconComponent"
            :active="active"
          />
          <RuiIcon v-else :name="icon" />
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
        <div class="flex grow py-0 text-capitalize navigation-menu-item__text">
          {{ text }}
        </div>
      </template>
      <div v-if="parent" class="text-rui-text-secondary">
        <RuiIcon
          name="arrow-down-s-line"
          class="transition-all transform"
          :class="{ 'rotate-180': subMenuExpanded }"
        />
      </div>
    </div>
    <div
      v-if="parent"
      :class="[
        css['submenu-wrapper'],
        {
          [`${css.expanded} submenu-wrapper__expanded`]: subMenuExpanded
        }
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

  &.active {
    @apply bg-rui-primary font-bold text-white hover:bg-rui-primary;

    .icon {
      @apply text-white;

      .image {
        @apply opacity-100 filter brightness-0 invert;
      }
    }
  }

  &.submenu {
    @apply pl-12 text-sm;
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
    }

    .icon {
      .image {
        @apply opacity-100 brightness-0 invert;
      }
    }
  }
}
</style>
