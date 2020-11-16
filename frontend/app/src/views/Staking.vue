<template>
  <v-container class="staking">
    <base-page-header :text="$t('staking.title')" />
    <v-container class="staking__content">
      <div
        v-if="!premium"
        class="staking__empty d-flex flex-column align-center"
      >
        <v-row align="center" justify="center">
          <v-col cols="auto" class="staking__logo">
            <v-img
              contain
              :max-width="$vuetify.breakpoint.mobile ? '100px' : '200px'"
              :src="require('@/assets/images/rotkehlchen_no_text.png')"
            />
          </v-col>
        </v-row>
        <v-row class="text-center">
          <v-col>
            <p class="text-h5">{{ $t('staking.no_premium') }}</p>
            <i18n path="staking.get_premium" tag="p" class="text-h6">
              <base-external-link text="website." :href="$interop.premiumURL" />
            </i18n>
          </v-col>
        </v-row>
      </div>
      <div v-else>
        <progress-screen v-if="loading">
          <template #message>
            {{ $t('staking.loading') }}
          </template>
        </progress-screen>
        <eth2-staking v-else />
      </div>
    </v-container>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import { Eth2Staking } from '@/utils/premium';

@Component({
  components: {
    ProgressScreen,
    BaseExternalLink,
    BasePageHeader,
    Eth2Staking
  }
})
export default class Staking extends Mixins(PremiumMixin, StatusMixin) {
  readonly section = Section.STAKING_ETH2;
}
</script>

<style scoped lang="scss">
.staking {
  height: 100%;

  &__content {
    height: 100%;
  }

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
