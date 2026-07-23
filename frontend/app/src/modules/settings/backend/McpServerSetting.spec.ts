import type { McpServerStatus } from '@shared/ipc';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import McpServerSetting from '@/modules/settings/backend/McpServerSetting.vue';

const mocks = vi.hoisted(() => ({
  getMcpServerStatus: vi.fn(),
  setMcpAutoStart: vi.fn(),
  startMcpServer: vi.fn(),
  stopMcpServer: vi.fn(),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): Record<string, unknown> => ({
    ...mocks,
    isPackaged: true,
  }),
}));

const stoppedStatus: McpServerStatus = {
  autoStart: false,
  endpoint: 'http://127.0.0.1:4445/mcp',
  state: 'Idle',
};

function createWrapper(): VueWrapper<InstanceType<typeof McpServerSetting>> {
  return mount(McpServerSetting, {
    global: {
      stubs: {
        CopyTooltip: {
          props: ['value'],
          template: '<div class="copy-tooltip" :data-value="value"><slot /><slot name="label" /></div>',
        },
        RuiAlert: {
          template: '<div class="rui-alert"><slot /></div>',
        },
        RuiButton: {
          emits: ['click'],
          template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
        },
        RuiChip: {
          template: '<span class="rui-chip"><slot /></span>',
        },
        RuiIcon: true,
        RuiSwitch: {
          emits: ['update:modelValue'],
          props: ['modelValue'],
          template: '<button v-bind="$attrs" class="rui-switch" @click="$emit(\'update:modelValue\', !modelValue)" />',
        },
        SettingsItem: {
          template: '<section><slot name="title" /><slot name="subtitle" /><slot /></section>',
        },
      },
    },
  });
}

describe('mcpServerSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getMcpServerStatus.mockResolvedValue(stoppedStatus);
    mocks.setMcpAutoStart.mockImplementation(async (enabled: boolean) => ({
      ...stoppedStatus,
      autoStart: enabled,
    }));
    mocks.startMcpServer.mockResolvedValue({ ...stoppedStatus, state: 'Ready' });
    mocks.stopMcpServer.mockResolvedValue(stoppedStatus);
  });

  it('should show the managed endpoint and stopped state by default', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(mocks.getMcpServerStatus).toHaveBeenCalledOnce();
    expect(wrapper.find('code').text()).toBe(stoppedStatus.endpoint);
    expect(wrapper.find('.copy-tooltip').attributes('data-value')).toBe(stoppedStatus.endpoint);
    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.stopped');
  });

  it('should persist auto-start without starting the server', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid="mcp-auto-start"]').trigger('click');
    await flushPromises();

    expect(mocks.setMcpAutoStart).toHaveBeenCalledWith(true);
    expect(mocks.startMcpServer).not.toHaveBeenCalled();
  });

  it('should start and stop the server on demand', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid="mcp-lifecycle"]').trigger('click');
    await flushPromises();
    expect(mocks.startMcpServer).toHaveBeenCalledOnce();

    await wrapper.find('[data-testid="mcp-lifecycle"]').trigger('click');
    await flushPromises();
    expect(mocks.stopMcpServer).toHaveBeenCalledOnce();
  });
});
