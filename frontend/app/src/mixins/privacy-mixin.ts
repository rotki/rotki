import { Component, Vue } from 'vue-property-decorator';
import { mapState, mapGetters } from 'vuex';

@Component({
  computed: {
    ...mapState('session', ['privacyMode']),
    ...mapGetters('session', ['shouldShowAmount', 'shouldShowPercentage'])
  }
})
export default class PrivacyMixin extends Vue {
  privacyMode!: number;
  shouldShowAmount!: boolean;
  shouldShowPercentage!: boolean;

  get amountPrivacyStyle(): { [cssClass: string]: string } | null {
    return !this.shouldShowAmount
      ? {
          filter: 'blur(0.75em)'
        }
      : null;
  }
  get percentagePrivacyStyle(): { [cssClass: string]: string } | null {
    return !this.shouldShowPercentage
      ? {
          filter: 'blur(0.75em)'
        }
      : null;
  }
}
