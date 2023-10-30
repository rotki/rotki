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

const iconStyle = computed(() => ({
  fontSize: props.size
}));

const { locationData } = useLocations();

const location = locationData(item);

const css = useCssModule();
</script>

<template>
  <span
    class="flex items-center justify-center icon-bg"
    data-cy="location-icon"
    :class="{
      'flex-row': horizontal,
      'flex-col': !horizontal,
      'py-4': !noPadding,
      skeleton: !location,
      [css.wrapper]: icon
    }"
    @click="emit('click', item)"
  >
    <template v-if="location">
      <img
        v-if="location.image"
        :width="size"
        :height="size"
        class="object-contain dark:p-[0.1rem]"
        :class="css.icon"
        :src="location.image"
        :alt="location.name"
      />
      <RuiIcon
        v-else
        color="secondary"
        :name="location.icon"
        :style="iconStyle"
      />
      <span
        v-if="!icon"
        class="text-capitalize"
        :class="horizontal ? 'ml-3' : null"
      >
        {{ location.name }}
      </span>
    </template>
  </span>
</template>

<style lang="scss" module>
.wrapper {
  height: v-bind(size);
  width: v-bind(size);
}

.icon {
  max-height: calc(v-bind(size) - 0.1rem);
  max-width: calc(v-bind(size) - 0.1rem);
}
</style>
