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
    class="flex items-center justify-center gap-1"
    data-cy="location-icon"
    :class="{
      'flex-row': horizontal,
      'flex-col': !horizontal,
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
        class="object-contain dark:p-[0.1rem] icon-bg"
        :class="css.icon"
        :src="location.image"
        :alt="location.name"
      />
      <RuiIcon
        v-else
        color="secondary"
        class="icon-bg dark:p-[0.1rem]"
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
.wrapper {
  height: v-bind(size);
  width: v-bind(size);
}

.icon {
  height: v-bind(size);
  width: v-bind(size);
}
</style>
