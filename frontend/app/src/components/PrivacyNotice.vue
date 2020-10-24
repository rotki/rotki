<template>
  <div class="privacy-notice">
    <v-alert outlined dense color="primary" class="privacy-notice__message">
      <div>{{ $t('privacy_notice.title') }}</div>
      <div>{{ $t('privacy_notice.message') }}</div>
    </v-alert>
  </div>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class PrivacyNotice extends Vue {}
</script>
<style scoped lang="scss">
.privacy-notice {
  width: 100%;
  max-width: 600px;
  position: absolute;
  left: 0;
  right: 0;
  margin-right: auto;
  margin-left: auto;
  bottom: 20px;
  z-index: 4;
  align-items: center;
  display: flex;
  flex-direction: column;

  &__message {
    text-align: center;
    max-width: 650px;
    font-size: 14px !important;
    background: #e0e0e0 !important;
  }
}
</style>
