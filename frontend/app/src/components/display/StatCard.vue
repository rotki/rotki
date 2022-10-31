<template>
  <v-card class="stat-card d-flex flex-columns pa-0 fill-height">
    <div v-if="bordered" class="stat-card__border">
      <div class="stat-card__image ma-2">
        <v-img
          v-if="protocolIcon"
          contain
          alt="Protocol Logo"
          height="36px"
          width="36px"
          :src="protocolIcon"
        />
      </div>
      <div
        class="stat-card__border__gradient"
        :class="
          $vuetify.theme.dark
            ? 'stat-card__border__gradient--dark'
            : 'stat-card__border__gradient--light'
        "
      />
    </div>
    <div class="stat-card__content flex-grow-1">
      <v-card-title>
        <span v-if="title">
          <card-title>{{ title }}</card-title>
        </span>
        <v-spacer v-if="locked" />
        <premium-lock v-if="locked" />
      </v-card-title>
      <v-card-text>
        <span v-if="!locked && loading">
          <v-progress-linear indeterminate color="primary" />
        </span>
        <slot v-else-if="!locked" />
      </v-card-text>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import PremiumLock from '@/components/premium/PremiumLock.vue';

defineProps({
  title: { required: false, type: String, default: '' },
  locked: { required: false, type: Boolean, default: false },
  loading: { required: false, type: Boolean, default: false },
  protocolIcon: { required: false, type: String, default: '' },
  bordered: { required: false, type: Boolean, default: false }
});
</script>

<style scoped lang="scss">
.stat-card {
  width: 100%;
  min-height: 130px;

  &__image {
    z-index: 1;
  }

  :deep() {
    .v-card {
      &__text {
        font-size: 1em;
      }
    }
  }

  &__border {
    width: 48px;
    border-radius: 4px 0 0 4px !important;
    background-color: var(--v-rotki-light-grey-darken1);

    &__gradient {
      display: block;
      position: absolute;
      top: 0;
      left: 0;
      height: 100%;
      width: 48px;

      &--light {
        background: linear-gradient(
          115deg,
          rgba(255, 0, 0, 0),
          rgba(255, 255, 255, 0.6)
        );
      }

      &--dark {
        background: linear-gradient(115deg, rgba(30, 30, 30, 0), #272727);
      }
    }
  }
}
</style>
