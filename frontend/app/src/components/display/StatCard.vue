<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    locked?: boolean;
    loading?: boolean;
    protocolIcon?: string;
    bordered?: boolean;
  }>(),
  {
    title: '',
    locked: false,
    loading: false,
    protocolIcon: '',
    bordered: false
  }
);
const { dark } = useTheme();
</script>

<template>
  <VCard class="stat-card flex flex-columns pa-0 h-full overflow-hidden">
    <div v-if="bordered" class="stat-card__border">
      <div class="stat-card__image ma-2">
        <VImg
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
          dark
            ? 'stat-card__border__gradient--dark'
            : 'stat-card__border__gradient--light'
        "
      />
    </div>
    <div class="stat-card__content grow">
      <VCardTitle>
        <span v-if="title">
          <CardTitle>{{ title }}</CardTitle>
        </span>
        <div v-if="locked" class="grow" />
        <PremiumLock v-if="locked" />
      </VCardTitle>
      <VCardText>
        <span v-if="!locked && loading">
          <VProgressLinear indeterminate color="primary" />
        </span>
        <slot v-else-if="!locked" />
      </VCardText>
    </div>
  </VCard>
</template>

<style scoped lang="scss">
.stat-card {
  width: 100%;
  min-height: 130px;

  &__image {
    z-index: 1;
  }

  /* stylelint-disable selector-class-pattern,selector-nested-pattern */

  :deep(.v-card__text) {
    font-size: 1em;
  }

  /* stylelint-enable selector-class-pattern,selector-nested-pattern */

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
