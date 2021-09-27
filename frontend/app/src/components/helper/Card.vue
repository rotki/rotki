<template>
  <v-card v-bind="$attrs" v-on="$listeners">
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
    <v-card-actions v-if="$slots.buttons">
      <slot name="buttons" />
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import CardTitle from '@/components/typography/CardTitle.vue';

const Card = defineComponent({
  name: 'Card',
  components: { CardTitle },
  props: {
    outlinedBody: { required: false, type: Boolean, default: false },
    contained: { required: false, type: Boolean, default: false }
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
  max-height: calc(100vh - 200px);
  overflow-y: scroll;

  @extend .themed-scrollbar;
}
</style>
