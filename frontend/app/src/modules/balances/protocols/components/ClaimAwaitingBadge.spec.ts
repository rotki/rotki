import type { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';
import { bigNumberify, type ClaimRequest, type ProtocolBalance } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import ClaimAwaitingBadge from '@/modules/balances/protocols/components/ClaimAwaitingBadge.vue';
import '@test/i18n';

vi.mock('@/modules/balances/protocols/use-protocol-data', async () => {
  const { computed } = await import('vue');
  return {
    useProtocolData: (protocol: () => string): ReturnType<typeof useProtocolData> => ({
      protocolData: computed(() => (protocol() === 'lido' ? { icon: 'lu-x', name: 'Lido eth', type: 'icon' } : undefined)),
    }),
  };
});

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): Record<string, unknown> => ({
    scrambleIdentifier: (id: string) => `scrambled-${id}`,
  }),
}));

const RuiMenuStub = defineComponent({
  name: 'RuiMenu',
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
});

const RuiTooltipStub = defineComponent({
  name: 'RuiTooltip',
  props: { disabled: { default: false, type: Boolean } },
  template: '<div><slot name="activator" /><div v-if="!disabled" data-testid="tooltip-content"><slot /></div></div>',
});

const HashLinkStub = defineComponent({
  name: 'HashLink',
  props: ['text', 'location'],
  template: '<span data-testid="hash-link">{{ text }}</span>',
});

const DateDisplayStub = defineComponent({
  name: 'DateDisplay',
  props: ['timestamp'],
  template: '<span data-testid="date">{{ timestamp }}</span>',
});

const I18nTStub = defineComponent({
  name: 'I18nT',
  props: ['keypath'],
  template: '<span :data-keypath="keypath"><slot name="date" /><slot name="amount" /><slot name="protocol" /></span>',
});

function request(overrides: Partial<ClaimRequest> = {}): ClaimRequest {
  return {
    account: { address: '0xA', chain: 'base' },
    amount: bigNumberify('5.85'),
    availableAt: 4_102_444_800,
    finalized: false,
    ...overrides,
  };
}

function balance(overrides: Partial<ProtocolBalance> = {}): ProtocolBalance {
  return {
    amount: bigNumberify(10),
    awaitingClaim: bigNumberify('5.85'),
    claims: [request()],
    protocol: 'venice',
    value: bigNumberify(10),
    ...overrides,
  };
}

function createWrapper(
  protocolBalance: ProtocolBalance,
  compact = false,
): VueWrapper<InstanceType<typeof ClaimAwaitingBadge>> {
  return mount(ClaimAwaitingBadge, {
    global: {
      stubs: {
        AssetAmountDisplay: true,
        DateDisplay: DateDisplayStub,
        ExternalLink: defineComponent({ props: ['url'], template: '<a :href="url"><slot /></a>' }),
        HashLink: HashLinkStub,
        I18nT: I18nTStub,
        RuiIcon: true,
        RuiMenu: RuiMenuStub,
        RuiTooltip: RuiTooltipStub,
        ValueDisplay: true,
      },
    },
    props: { asset: 'VVV', compact, protocolBalance },
  });
}

describe('claimAwaitingBadge', () => {
  it('should label the badge unless compact', () => {
    expect(createWrapper(balance()).find('[data-testid="claim-awaiting-badge"] [data-keypath="claims.status.unlocks"]').exists()).toBe(true);
    expect(createWrapper(balance(), true).get('[data-testid="claim-awaiting-badge"]').text()).toBe('');
  });

  it('should label a request without an unlock date as pending', () => {
    const wrapper = createWrapper(balance({ claims: [request({ availableAt: undefined, requestedAt: 1700000000 })] }));

    expect(wrapper.get('[data-testid="claim-awaiting-badge"]').text()).toBe('claims.status.pending');
  });

  it('should explain the compact badge in a tooltip', () => {
    const pending = createWrapper(balance(), true);
    const ready = createWrapper(balance({ claims: [request({ finalized: true })], protocol: 'lido' }), true);

    expect(pending.get('[data-testid="claim-awaiting-tooltip"]').attributes('data-keypath')).toBe('claims.tooltip.pending');
    expect(ready.get('[data-testid="claim-awaiting-tooltip"]').attributes('data-keypath')).toBe('claims.tooltip.ready');
    expect(ready.get('[data-testid="claim-awaiting-tooltip"]').text()).toContain('Lido eth');
  });

  it('should not show a tooltip on the labelled badge', () => {
    expect(createWrapper(balance()).find('[data-testid="claim-awaiting-tooltip"]').exists()).toBe(false);
  });

  it('should name the protocol the way the breakdown row does', () => {
    expect(createWrapper(balance({ protocol: 'lido' })).get('[data-testid="claim-awaiting-heading"]').text()).toBe('claims.requests::1, Lido eth');
    expect(createWrapper(balance({ protocol: 'venice' })).get('[data-testid="claim-awaiting-heading"]').text()).toBe('claims.requests::1, Venice');
  });

  it('should list every account that has to claim once', () => {
    const wrapper = createWrapper(balance({
      claims: [
        request({ account: { address: '0xA', chain: 'base' }, id: '1' }),
        request({ account: { address: '0xA', chain: 'base' }, id: '2' }),
        request({ account: { address: '0xB', chain: 'base' }, id: '3' }),
      ],
    }));

    expect(wrapper.findAll('[data-testid="hash-link"]').map(link => link.text())).toEqual(['0xA', '0xB']);
  });

  it('should show one row per request with its status and date', () => {
    const wrapper = createWrapper(balance({
      claims: [
        request({ availableAt: undefined, finalized: true, id: '1' }),
        request({ availableAt: undefined, id: '2', requestedAt: 1700000000 }),
        request({ availableAt: 4_102_444_800 }),
      ],
    }));

    const rows = wrapper.findAll('[data-testid="claim-awaiting-request"]');
    expect(rows).toHaveLength(3);
    expect(rows[0].text()).toContain('#scrambled-1');
    expect(rows[0].text()).toContain('claims.request.ready');
    expect(rows[1].find('[data-keypath="claims.request.requested"]').exists()).toBe(true);
    expect(rows[1].get('[data-testid="date"]').text()).toBe('1700000000');
    expect(rows[2].find('[data-keypath="claims.request.ready_on"]').exists()).toBe(true);
    expect(rows[2].get('[data-testid="date"]').text()).toBe('4102444800');
  });

  it('should show the request number through the scramble setting', () => {
    const wrapper = createWrapper(balance({ claims: [request({ id: '122427' })] }));

    expect(wrapper.get('[data-testid="claim-awaiting-request"]').text()).toContain('#scrambled-122427');
    expect(wrapper.text()).not.toContain('#122427');
  });

  it('should turn the badge into ready to claim as soon as one request is ready', () => {
    const pending = createWrapper(balance());
    const ready = createWrapper(balance({ claims: [request({ finalized: true })] }));

    expect(pending.get('[data-testid="claim-awaiting-badge"]').attributes('aria-label')).toBe('claims.status.pending');
    expect(ready.get('[data-testid="claim-awaiting-badge"]').attributes('aria-label')).toBe('claims.status.ready');
  });

  it('should link to the protocol claim page only when it has one', () => {
    expect(createWrapper(balance()).get('[data-testid="claim-awaiting-link"]').attributes('href')).toBe('https://venice.ai/token');
    expect(createWrapper(balance({ protocol: 'other' })).find('[data-testid="claim-awaiting-link"]').exists()).toBe(false);
  });

  it('should leave out the account list when no account is known', () => {
    const wrapper = createWrapper(balance({ claims: [request({ account: undefined })] }));

    expect(wrapper.find('[data-testid="claim-awaiting-accounts"]').exists()).toBe(false);
  });
});

const MenuStateStub = defineComponent({
  name: 'RuiMenu',
  props: { modelValue: { default: undefined, type: Boolean } },
  template: '<div><slot name="activator" :attrs="{}" /></div>',
});

describe('claimAwaitingBadge as part of a table row', () => {
  function mountInRow(onRowClick: () => void): VueWrapper<InstanceType<typeof ClaimAwaitingBadge>> {
    const row = document.createElement('div');
    row.addEventListener('click', onRowClick);
    document.body.appendChild(row);

    return mount(ClaimAwaitingBadge, {
      attachTo: row,
      global: { stubs: { AssetAmountDisplay: true, HashLink: HashLinkStub, RuiIcon: true, RuiMenu: MenuStateStub, RuiTooltip: RuiTooltipStub } },
      props: { asset: 'VVV', protocolBalance: balance() },
    });
  }

  it('should start with the popover closed', () => {
    const wrapper = mountInRow(vi.fn());

    expect(wrapper.getComponent(MenuStateStub).props('modelValue')).toBe(false);
  });

  it('should not toggle the row that contains the badge', async () => {
    const onRowClick = vi.fn<() => void>();
    const wrapper = mountInRow(onRowClick);

    await wrapper.get('[data-testid="claim-awaiting-badge"]').trigger('click');

    expect(onRowClick).not.toHaveBeenCalled();
  });
});
