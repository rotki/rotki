import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';

@Component({
  computed: {
    ...mapState('session', ['premium'])
  }
})
export default class PremiumMixin extends Vue {
  premium!: boolean;
}
