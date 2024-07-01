<script setup lang="ts">
const props = defineProps<{
  event: { counterparty: string | null; address?: string | null };
}>();

const { event } = toRefs(props);

const { getEventCounterpartyData } = useHistoryEventCounterpartyMappings();

const counterparty = getEventCounterpartyData(event);
const imagePath = '/assets/images/protocols/';
</script>

<template>
  <RuiBadge
    v-if="counterparty || event.address"
    class="[&_span]:!px-0"
    color="default"
    offset-x="-4"
    offset-y="4"
  >
    <template #icon>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <div class="rounded-full overflow-hidden bg-white">
            <template v-if="counterparty">
              <RuiIcon
                v-if="counterparty.icon"
                :name="counterparty.icon"
                :color="counterparty.color"
              />

              <AppImage
                v-else-if="counterparty.image"
                :src="`${imagePath}${counterparty.image}`"
                contain
                size="20px"
              />

              <EnsAvatar
                v-else
                size="20px"
                :address="counterparty.label"
              />
            </template>
            <EnsAvatar
              v-else-if="event.address"
              size="20px"
              :address="event.address"
              avatar
            />
          </div>
        </template>
        <div>{{ counterparty?.label || event?.address }}</div>
      </RuiTooltip>
    </template>
    <slot />
  </RuiBadge>
  <div v-else>
    <slot />
  </div>
</template>
