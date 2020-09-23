<template>
  <div :id="`${name}_badge`" class="exchange-badge">
    <v-img
      :title="name"
      width="50px"
      contain
      class="exchange-badge__icon ml-2 mr-2"
      :src="require(`@/assets/images/${name}.png`)"
      :alt="$t('exchange_badge.icon_alt')"
    />

    <div class="exchange-badge__name ml-2 mr-1">{{ name }}</div>
    <v-tooltip v-if="removeable" top open-delay="400">
      <template #activator="{ on, attrs }">
        <v-btn
          small
          icon
          class="mr-1"
          color="primary"
          v-bind="attrs"
          v-on="on"
          @click="remove"
        >
          <v-icon small>mdi-close</v-icon>
        </v-btn>
      </template>
      <span>{{ $t('exchange_badge.remove_tooltip') }}</span>
    </v-tooltip>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ExchangeBadge extends Vue {
  @Prop({ required: true, type: String })
  name!: string;
  @Prop({ required: false, type: Boolean, default: false })
  removeable!: boolean;

  @Emit()
  remove() {}
}
</script>

<style scoped lang="scss">
.exchange-badge {
  display: flex;
  flex-direction: row;
  align-items: center;
  height: 60px;
  border: var(--v-rotki-light-grey-darken1) solid thin;
  border-radius: 8px;

  &__icon {
    filter: grayscale(100%);
  }

  &__name {
    font-size: 30px;
  }
}
</style>
