<script setup lang="ts">
defineProps<{ text: string }>();

const { t } = useI18n();

const { premiumURL } = useInterop();
const { mobile } = useDisplay();
const css = useCssModule();
const remoteEmptyScreenLogo =
  'https://raw.githubusercontent.com/rotki/data/main/assets/icons/empty_screen_logo.png';
</script>

<template>
  <FullSizeContent>
    <VRow align="center" justify="center">
      <VCol cols="12">
        <VRow align="center" justify="center">
          <VCol cols="auto">
            <div :class="css.logo" class="flex justify-center items-center">
              <RotkiLogo
                :width="mobile ? '100px' : '200px'"
                :url="remoteEmptyScreenLogo"
              />
            </div>
          </VCol>
        </VRow>
        <VRow class="text-center mt-14">
          <VCol>
            <p class="text-h5 font-bold pb-4">
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
              <BaseExternalLink
                text="website."
                :href="premiumURL"
                class="font-medium"
              />
            </i18n>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </FullSizeContent>
</template>

<style module lang="scss">
.logo {
  padding: 80px;
  border-radius: 50%;
  background-color: var(--v-rotki-light-grey-darken1);
}
</style>
