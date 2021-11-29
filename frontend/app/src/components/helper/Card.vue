<template>
  <v-card
    v-bind="$attrs"
    :class="{
      [$style['no-radius-bottom']]: noRadiusBottom
    }"
    v-on="$listeners"
  >
    <v-card-title v-if="$slots.title">
      <slot v-if="$slots.icon" name="icon" />
      <card-title
        :class="{
          'ps-1': $slots.icon,
          [$style.title]: $slots.icon
        }"
      >
        <slot name="title" />
      </card-title>
      <v-spacer v-if="$slots.details" />
      <slot name="details" />
    </v-card-title>
    <v-card-subtitle v-if="$slots.subtitle">
      <div
        :class="{
          'ps-13': $slots.icon,
          [$style.subtitle]: $slots.icon
        }"
      >
        <slot name="subtitle" />
      </div>
    </v-card-subtitle>
    <v-card-text
      ref="body"
      :style="bodyStyle"
      :class="{
        [$style.contained]: contained
      }"
    >
      <slot name="search" />
      <v-sheet v-if="$slots.actions" outlined rounded class="pa-3 mb-4">
        <slot name="actions" />
      </v-sheet>
      <div v-if="$slots.hint" class="pb-4">
        <slot name="hint" />
      </div>
      <v-sheet v-if="outlinedBody" outlined rounded>
        <slot />
      </v-sheet>
      <slot v-else />
      <div v-if="$slots.options" :class="$style.options">
        <slot name="options" />
      </div>
    </v-card-text>
    <v-card-actions v-if="$slots.buttons" ref="actions" :class="$style.actions">
      <slot name="buttons" />
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  ref,
  toRefs
} from '@vue/composition-api';
import CardTitle from '@/components/typography/CardTitle.vue';

const Card = defineComponent({
  name: 'Card',
  components: { CardTitle },
  props: {
    outlinedBody: { required: false, type: Boolean, default: false },
    contained: { required: false, type: Boolean, default: false },
    noRadiusBottom: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { contained } = toRefs(props);
    const body = ref<HTMLDivElement | null>(null);
    const actions = ref<HTMLDivElement | null>(null);
    const top = ref(206);

    onMounted(() => {
      setTimeout(() => {
        top.value = body.value?.getBoundingClientRect().top ?? 0;
      }, 1000);
    });

    const bodyStyle = computed(() => {
      if (!contained.value) {
        return null;
      }
      const bodyTop = top.value;
      const actionsHeight = actions.value?.getBoundingClientRect().height ?? 0;
      const diff = bodyTop + actionsHeight;

      return {
        height: `calc(100vh - ${diff}px)`
      };
    });

    return {
      actions,
      body,
      bodyStyle
    };
  }
});

export default Card;
</script>

<style module lang="scss">
@import '~@/scss/scroll';

.title {
  margin-top: -22px;
}

.subtitle {
  margin-top: -40px;
}

.options {
  margin-bottom: -36px;
}

.contained {
  max-height: calc(100vh - 206px);
  overflow-y: scroll;

  @extend .themed-scrollbar;
}

.no-radius-bottom {
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}

.actions {
  padding: 16px !important;
}
</style>
