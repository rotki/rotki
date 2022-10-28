<template>
  <full-size-content>
    <v-row align="center" justify="center">
      <v-col cols="12">
        <v-row align="center" justify="center">
          <v-col cols="auto">
            <div :class="$style.logo">
              <v-img
                contain
                :class="$style.image"
                src="/assets/images/rotkehlchen_no_text.png"
              />
            </div>
          </v-col>
        </v-row>
        <v-row class="text-center mt-14">
          <v-col>
            <p class="text-h5 font-weight-bold pb-4">
              {{ t('no_premium_placeholder.no_premium') }}
            </p>
            <div class="text--secondary text-no-wrap">
              {{ t('no_premium_placeholder.premium_only', { text }) }}
            </div>
            <i18n
              path="no_premium_placeholder.get_premium"
              tag="p"
              class="text--secondary"
            >
              <base-external-link
                text="website."
                :href="interop.premiumURL"
                class="font-weight-medium"
              />
            </i18n>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </full-size-content>
</template>

<script setup lang="ts">
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import { interop } from '@/electron-interop';

defineProps({
  text: {
    type: String,
    required: true
  }
});

const { t } = useI18n();
</script>

<style module lang="scss">
.logo {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 300px !important;
  height: 300px !important;
  border-radius: 50%;
  background-color: var(--v-rotki-light-grey-darken1);

  @media only screen and (max-width: 400px) {
    width: 200px !important;
    height: 200px !important;
  }
}

.image {
  width: 160px !important;
  height: 160px !important;

  @media only screen and (max-width: 400px) {
    width: 110px !important;
    height: 110px !important;
  }
}
</style>
