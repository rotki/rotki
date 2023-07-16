<script setup lang="ts">
import { useListeners } from 'vue';

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
const css = useCssModule();
const slots = useSlots();
const rootAttrs = useAttrs();
const rootListeners = useListeners();

const { contained } = toRefs(props);
const body = ref<HTMLDivElement | null>(null);
const actions = ref<HTMLDivElement | null>(null);
const top = ref(206);

onMounted(() => {
  setTimeout(() => {
    set(top, get(body)?.getBoundingClientRect().top ?? 0);
  }, 1000);
});

const bodyStyle = computed(() => {
  if (!get(contained)) {
    return null;
  }
  const bodyTop = get(top);
  const actionsHeight = get(actions)?.getBoundingClientRect().height ?? 0;
  const diff = bodyTop + actionsHeight;

  return {
    height: `calc(100vh - ${diff}px)`
  };
});
</script>

<template>
  <VCard
    v-bind="rootAttrs"
    :flat="flat"
    :class="{
      [css['no-radius-bottom']]: noRadiusBottom,
      [css['full-height']]: fullHeight
    }"
    v-on="rootListeners"
  >
    <VCardTitle v-if="slots.title" :class="{ 'pt-6': slots.icon }">
      <slot v-if="slots.icon" name="icon" />
      <CardTitle
        :class="{
          'ps-3': slots.icon,
          [css.title]: slots.icon
        }"
      >
        <slot name="title" />
      </CardTitle>
      <VSpacer v-if="slots.details" />
      <slot name="details" />
    </VCardTitle>
    <VCardSubtitle v-if="slots.subtitle" :class="{ 'ms-14': slots.icon }">
      <div
        :class="{
          'pt-2': slots.icon,
          [css.subtitle]: slots.icon
        }"
      >
        <slot name="subtitle" />
      </div>
    </VCardSubtitle>
    <VCardText
      ref="body"
      :style="bodyStyle"
      :class="{
        [css.contained]: contained,
        [css['no-padding']]: noPadding
      }"
    >
      <slot name="search" />
      <VSheet v-if="slots.actions" outlined rounded class="pa-3 mb-4">
        <slot name="actions" />
      </VSheet>
      <div v-if="slots.hint" class="pb-4">
        <slot name="hint" />
      </div>
      <VSheet v-if="outlinedBody" outlined rounded>
        <slot />
      </VSheet>
      <slot v-else />
      <div v-if="slots.options" :class="css.options">
        <slot name="options" />
      </div>
    </VCardText>
    <VCardActions v-if="slots.buttons" ref="actions" :class="css.actions">
      <slot name="buttons" />
    </VCardActions>
  </VCard>
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
  max-height: calc(100vh - 206px);
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
