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
    <v-card-text>
      <slot name="search" />
      <v-sheet v-if="$slots.actions" outlined rounded class="pa-3 mb-4">
        <slot name="actions" />
      </v-sheet>
      <v-sheet v-if="outlinedBody" outlined rounded>
        <slot />
      </v-sheet>
      <slot v-else />
    </v-card-text>
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
}
</script>

<style scoped lang="scss">
.card {
  &__title {
    margin-top: -22px;
  }

  &__subtitle {
    margin-top: -40px;
  }
}
</style>
