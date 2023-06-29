<script setup lang="ts">
import { useListeners } from 'vue';

const css = useCssModule();
const slots = useSlots();
const rootAttrs = useAttrs();
const rootListeners = useListeners();

const props = withDefaults(
  defineProps<{
    outlinedBody?: boolean;
    contained?: boolean;
    noRadiusBottom?: boolean;
    fullHeight?: boolean;
    noPadding?: boolean;
    flat?: boolean;
  }>(),
  {
    outlinedBody: false,
    contained: false,
    noRadiusBottom: false,
    noPadding: false,
    fullHeight: false,
    flat: false
  }
);

const { contained } = toRefs(props);
const titleRef = ref<HTMLDivElement | null>(null);
const subTitleRef = ref<HTMLDivElement | null>(null);
const actionsRef = ref<HTMLDivElement | null>(null);

const { height: titleHeight } = useElementBounding(titleRef);
const { height: subTitleHeight } = useElementBounding(subTitleRef);
const { height: actionsHeight } = useElementBounding(actionsRef);

const otherHeights = computed(() => {
  const subTitleHeightVal = get(subTitleHeight) ?? 0;
  const totalHeight =
    (get(titleHeight) ?? 0) +
    (subTitleHeightVal > 0 ? subTitleHeightVal - 16 : subTitleHeightVal) +
    (get(actionsHeight) ?? 0);
  return `${totalHeight}px`;
});
</script>

<template>
  <v-card
    v-bind="rootAttrs"
    :flat="flat"
    :class="{
      [css['no-radius-bottom']]: noRadiusBottom,
      [css['full-height']]: fullHeight
    }"
    v-on="rootListeners"
  >
    <v-card-title
      v-if="slots.title"
      ref="titleRef"
      :class="{ 'pt-6': slots.icon }"
    >
      <slot v-if="slots.icon" name="icon" />
      <card-title
        :class="{
          'ps-3': slots.icon,
          [css.title]: slots.icon
        }"
      >
        <slot name="title" />
      </card-title>
      <v-spacer v-if="slots.details" />
      <slot name="details" />
    </v-card-title>
    <v-card-subtitle
      v-if="slots.subtitle"
      ref="subTitleRef"
      :class="{ 'ms-14': slots.icon }"
    >
      <div
        :class="{
          'pt-2': slots.icon,
          [css.subtitle]: slots.icon
        }"
      >
        <slot name="subtitle" />
      </div>
    </v-card-subtitle>
    <v-card-text
      :class="{
        [css.contained]: contained,
        [css['no-padding']]: noPadding
      }"
    >
      <slot name="search" />
      <v-sheet v-if="slots.actions" outlined rounded class="pa-3 mb-4">
        <slot name="actions" />
      </v-sheet>
      <div v-if="slots.hint" class="pb-4">
        <slot name="hint" />
      </div>
      <v-sheet v-if="outlinedBody" outlined rounded>
        <slot />
      </v-sheet>
      <slot v-else />
      <div v-if="slots.options" :class="css.options">
        <slot name="options" />
      </div>
    </v-card-text>
    <v-card-actions v-if="slots.buttons" ref="actionsRef" :class="css.actions">
      <slot name="buttons" />
    </v-card-actions>
  </v-card>
</template>

<style module lang="scss">
.title {
  margin-top: -22px;
}

.subtitle {
  margin-top: -40px;
  margin-left: 18px;
}

.options {
  margin-bottom: -36px;
}

.contained {
  height: calc(90vh - v-bind(otherHeights));
  overflow-y: scroll;
}

.no-radius-bottom {
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}

.actions {
  padding: 16px !important;
}

.no-padding {
  padding: 0 !important;
}

.full-height {
  height: 100%;
}
</style>
