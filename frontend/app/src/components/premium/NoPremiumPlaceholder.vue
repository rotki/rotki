<template>
  <full-size-content>
    <v-row align="center" justify="center">
      <v-col cols="auto" :class="$style.logo">
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
  </full-size-content>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import FullSizeContent from '@/components/common/FullSizeContent.vue';

export default defineComponent({
  name: 'NoPremiumPlaceholder',
  components: { FullSizeContent, BaseExternalLink },
  props: {
    text: {
      type: String,
      required: true
    }
  }
});
</script>

<style module lang="scss">
.logo {
  padding: 80px;
  border-radius: 50%;
  background-color: var(--v-rotki-light-grey-darken1);
}
</style>
