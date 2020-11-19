<template>
  <div
    class="no-premium-placeholder__empty d-flex flex-column align-center"
    :style="`height: calc(100vh - ${top + 64}px);`"
  >
    <v-row align="center" justify="center">
      <v-col cols="auto" class="no-premium-placeholder__logo">
        <v-img
          contain
          :max-width="$vuetify.breakpoint.mobile ? '100px' : '200px'"
          :src="require('@/assets/images/rotkehlchen_no_text.png')"
        />
      </v-col>
    </v-row>
    <v-row class="text-center">
      <v-col>
        <p class="text-h5">
          {{ $t('no_premium_placeholder.no_premium', { text }) }}
        </p>
        <i18n path="no_premium_placeholder.get_premium" tag="p" class="text-h6">
          <base-external-link text="website." :href="$interop.premiumURL" />
        </i18n>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';

@Component({
  components: { BaseExternalLink }
})
export default class NoPremiumPlaceholder extends Vue {
  @Prop({ required: true, type: String })
  text!: string;

  private top: number = -1;

  mounted() {
    const { top } = this.$el.getBoundingClientRect();
    this.top = top;
  }
}
</script>

<style scoped lang="scss">
.no-premium-placeholder {
  &__logo {
    padding: 80px;
    border-radius: 50%;
    background-color: var(--v-rotki-light-grey-darken1);
  }

  &__empty {
    height: 100%;
  }
}
</style>
