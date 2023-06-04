<script setup lang="ts">
const { t } = useI18n();

defineProps<{ text: string }>();

const { premiumURL } = useInterop();
const { mobile } = useDisplay();
const css = useCssModule();
const remoteEmptyScreenLogo =
  'https://raw.githubusercontent.com/rotki/data/main/assets/icons/empty_screen_logo.png';
</script>

<template>
  <full-size-content>
    <v-row align="center" justify="center">
      <v-col cols="12">
        <v-row align="center" justify="center">
          <v-col cols="auto">
            <div :class="css.logo" class="d-flex justify-center align-center">
              <rotki-logo
                :width="mobile ? '100px' : '200px'"
                :url="remoteEmptyScreenLogo"
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
                :href="premiumURL"
                class="font-weight-medium"
              />
            </i18n>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </full-size-content>
</template>

<style module lang="scss">
.logo {
  padding: 80px;
  border-radius: 50%;
  background-color: var(--v-rotki-light-grey-darken1);
}
</style>
