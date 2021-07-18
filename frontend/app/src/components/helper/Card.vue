<template>
  <v-card v-bind="$attrs" v-on="$listeners">
    <v-card-title v-if="$slots.title">
      <slot v-if="$slots.icon" name="icon" />
      <card-title :class="$slots.icon ? 'ps-1 card__title' : null">
        <slot name="title" />
      </card-title>
      <v-spacer v-if="$slots.details" />
      <slot name="details" />
    </v-card-title>
    <v-card-subtitle v-if="$slots.subtitle">
      <div :class="$slots.icon ? 'ps-13 card__subtitle' : null">
        <slot name="subtitle" />
      </div>
    </v-card-subtitle>
    <v-card-text :class="contained ? 'card__contained' : null">
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
      <div v-if="$slots.options" class="card__options">
        <slot name="options" />
      </div>
    </v-card-text>
    <v-card-actions v-if="$slots.buttons">
      <slot name="buttons" />
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import CardTitle from '@/components/typography/CardTitle.vue';

@Component({
  name: 'Card',
  components: { CardTitle }
})
export default class Card extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  outlinedBody!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  contained!: boolean;
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.card {
  &__title {
    margin-top: -22px;
  }

  &__subtitle {
    margin-top: -40px;
  }

  &__options {
    margin-bottom: -36px;
  }

  &__contained {
    max-height: calc(100vh - 200px);
    overflow-y: scroll;

    @extend .themed-scrollbar;
  }
}
</style>
