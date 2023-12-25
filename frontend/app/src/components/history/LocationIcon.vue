<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    item: string;
    horizontal?: boolean;
    icon?: boolean;
    size?: string;
    noPadding?: boolean;
  }>(),
  {
    horizontal: false,
    icon: false,
    size: '24px',
    noPadding: false
  }
);

const emit = defineEmits<{ (e: 'click', location: string): void }>();

const { item } = toRefs(props);

const { locationData } = useLocations();

const location = locationData(item);

const css = useCssModule();
</script>

<template>
  <div
    class="flex items-center justify-center"
    data-cy="location-icon"
    :class="{
      'flex-row gap-2': horizontal,
      'flex-col gap-1': !horizontal,
      skeleton: !location,
      [css.wrapper]: icon
    }"
    @click="emit('click', item)"
  >
    <template v-if="location">
      <AppImage
        v-if="location.image"
        :src="location.image"
        :alt="location.name"
        contain
        :size="size"
        class="icon-bg p-[0.1rem]"
      />
      <RuiIcon
        v-else
        color="secondary"
        class="icon-bg p-[0.1rem]"
        :size="size"
        :name="location.icon"
      />
      <span
        v-if="!icon"
        class="text-capitalize text-rui-text-secondary"
        :class="{
          '-mb-1': !horizontal
        }"
      >
        {{ location.name }}
      </span>
    </template>
  </div>
</template>

<style lang="scss" module>
.wrapper,
.icon {
  height: v-bind(size);
  width: v-bind(size);
}
</style>
