import type { SpamAssessment } from '@/modules/assets/spam/use-spam-assessments';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { msg } from '@/message-key';
import SpamAssessmentHint from '@/modules/assets/spam/SpamAssessmentHint.vue';
import DataIssuePanelCard from '@/modules/history/data-issues/components/DataIssuePanelCard.vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'eip155:1/erc20:0x1111111111111111111111111111111111111111',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id: 1,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    tsEnd: 1710000000,
    tsStart: 1710000000,
    ...overrides,
  };
}

function createWrapper(spamAssessment?: SpamAssessment): VueWrapper<InstanceType<typeof DataIssuePanelCard>> {
  return mount(DataIssuePanelCard, {
    global: {
      stubs: {
        AssetIcon: true,
        CounterpartyDisplay: true,
        DataIssueCardActions: true,
        DataIssueDescription: true,
        DataIssueKindChip: true,
        DataIssueStateChip: true,
        HistoryEventAccount: true,
        LocationDisplay: true,
        RuiCard: { template: '<div><slot /></div>' },
        RuiIcon: true,
        RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
        SpamAssessmentHint: true,
        TimeAgoDisplay: true,
      },
    },
    props: {
      description: {
        amounts: {},
        messageKey: msg.$t('data_issues.description.unknown'),
        shortMessageKey: msg.$t('data_issues.description_short.unknown'),
      },
      issue: createIssue(),
      spamAssessment,
    },
  });
}

describe('dataIssuePanelCard', () => {
  it('should show a standalone potential-spam badge when the asset is flagged', () => {
    const flagged: SpamAssessment = {
      prediction: {
        flagged: true,
        modelReasons: [],
        observedSignals: [],
        spamProbability: 0.94,
        threshold: 0.5,
      },
      status: 'ready',
    };
    const wrapper = createWrapper(flagged);

    const hint = wrapper.findComponent(SpamAssessmentHint);
    expect(hint.exists()).toBe(true);
    expect(hint.props('assessment')).toStrictEqual(flagged);
    expect(hint.props('standalone')).toBe(true);
  });

  it.each<{ label: string; assessment?: SpamAssessment }>([
    {
      assessment: {
        prediction: {
          flagged: false,
          modelReasons: [],
          observedSignals: [],
          spamProbability: 0.1,
          threshold: 0.5,
        },
        status: 'ready',
      },
      label: 'low-score',
    },
    { assessment: { status: 'loading' }, label: 'loading' },
    { assessment: { status: 'unsupported' }, label: 'unsupported' },
    { assessment: { status: 'unavailable' }, label: 'unavailable' },
    { assessment: undefined, label: 'missing' },
  ])('should hide the card spam badge for a $label assessment', ({ assessment }) => {
    const wrapper = createWrapper(assessment);

    expect(wrapper.findComponent(SpamAssessmentHint).exists()).toBe(false);
  });
});
