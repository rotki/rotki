<template>
  <div :id="`${name}_badge`" class="exchange-badge">
    <img
      :title="name"
      class="exchange-badge__icon"
      :src="require(`../assets/images/${name}.png`)"
      alt="Exchange icon"
    />
    <div class="exchange-badge__name">{{ name }}</div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ExchangeBadge extends Vue {
  @Prop({ required: true })
  name!: string;
}
</script>

<style scoped lang="scss">
.exchange-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  max-width: 95px;
  padding: 8px;
}

.exchange-badge__icon {
  width: 60px;
}

.exchange-badge__name {
  margin-top: 16px;
  font-size: 20px;
}
</style>
