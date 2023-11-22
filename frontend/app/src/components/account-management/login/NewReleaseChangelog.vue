<script setup lang="ts">
const { t } = useI18n();

const { version, link } = useUpdateMessage();
const { href, onLinkClick, linkTarget } = useLinks(link);
const css = useCssModule();
</script>

<template>
  <div class="flex flex-col align-start gap-4 w-full p-6" :class="css.card">
    <div class="bg-white rounded-[0.625rem] p-3">
      <RuiIcon color="primary" name="checkbox-circle-line" />
    </div>
    <div class="text-h6 text-rui-text">
      {{ t('welcome.update.title') }}
    </div>
    <div class="text-body-1 text-rui-text-secondary">
      {{ t('welcome.update.text', { version }) }}
    </div>

    <RuiButton
      tag="a"
      color="primary"
      :target="linkTarget"
      :href="href"
      @click="onLinkClick()"
    >
      {{ t('welcome.update.learn_more') }}
    </RuiButton>
  </div>
</template>

<style module lang="scss">
.card {
  background: rgba(78, 91, 166, 0.04);
}
</style>
