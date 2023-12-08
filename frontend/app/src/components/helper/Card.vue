<script setup lang="ts">
import { useListeners } from 'vue';

const props = withDefaults(
  defineProps<{
    contained?: boolean;
    fullHeight?: boolean;
    noPadding?: boolean;
    flat?: boolean;
    outlined?: boolean;
  }>(),
  {
    contained: false,
    noPadding: false,
    fullHeight: false,
    flat: false,
    outlined: true
  }
);
const css = useCssModule();
const slots = useSlots();
const rootAttrs = useAttrs();
const rootListeners = useListeners();

const { contained } = toRefs(props);
const cardRef = ref<HTMLDivElement>();
const bodyRef = ref<HTMLDivElement>();
const actionsRef = ref<HTMLDivElement>();

const { top: cardTop } = useElementBounding(cardRef);
const { top: bodyTop } = useElementBounding(bodyRef);
const { height: bottomHeight } = useElementBounding(actionsRef);

const otherHeights = computed(() => {
  const topHeight = get(bodyTop) - get(cardTop);
  const totalHeight = topHeight + get(bottomHeight);
  return `${totalHeight}px`;
});
</script>

<template>
  <VCard
    ref="cardRef"
    v-bind="rootAttrs"
    :flat="flat"
    :class="{
      ['h-full']: fullHeight
    }"
    :outlined="outlined"
    v-on="rootListeners"
  >
    <VCardTitle v-if="slots.title">
      <CardTitle>
        <slot name="title" />
      </CardTitle>
      <div v-if="slots.details" class="grow" />
      <slot name="details" />
    </VCardTitle>
    <VCardSubtitle v-if="slots.subtitle">
      <slot name="subtitle" />
    </VCardSubtitle>
    <VCardText
      ref="bodyRef"
      :class="{
        [css.contained]: contained,
        ['no-padding']: noPadding
      }"
    >
      <slot name="search" />
      <div v-if="slots.actions" class="mb-4">
        <slot name="actions" />
      </div>
      <div v-if="slots.hint" class="pb-4">
        <slot name="hint" />
      </div>
      <slot />
      <div v-if="slots.options" :class="css.options">
        <slot name="options" />
      </div>
    </VCardText>
    <VCardActions v-if="slots.buttons" ref="actionsRef">
      <slot name="buttons" />
    </VCardActions>
  </VCard>
</template>

<style module lang="scss">
.options {
  margin-bottom: -36px;
}

.contained {
  height: calc(90vh - v-bind(otherHeights));
  overflow-y: auto;
}
</style>
