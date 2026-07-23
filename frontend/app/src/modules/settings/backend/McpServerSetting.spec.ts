import type { McpServerStatus } from '@shared/ipc';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import McpServerSetting from '@/modules/settings/backend/McpServerSetting.vue';
import { setMcpServerState } from '@/modules/settings/backend/use-mcp-server-state';

const mocks = vi.hoisted(() => ({
  getMcpServerStatus: vi.fn(),
  isPackaged: true,
  setMcpAutoStart: vi.fn(),
  startMcpServer: vi.fn(),
  stopMcpServer: vi.fn(),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): Record<string, unknown> => ({
    ...mocks,
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
          props: ['disabled'],
          template: '<button v-bind="$attrs" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
        },
        RuiChip: {
          template: '<span class="rui-chip"><slot /></span>',
        },
        RuiIcon: true,
        RuiSwitch: {
          emits: ['update:modelValue'],
          props: ['disabled', 'modelValue'],
          template: '<button v-bind="$attrs" class="rui-switch" :disabled="disabled" @click="$emit(\'update:modelValue\', !modelValue)" />',
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
    mocks.isPackaged = true;
    setMcpServerState(undefined);
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

  it('should show a failed state when the managed MCP service crashes', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    setMcpServerState('Failed');
    await nextTick();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.failed');
  });

  it('should show lifecycle errors and refresh the service state', async () => {
    mocks.startMcpServer.mockRejectedValueOnce(new Error('start failed'));
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid="mcp-lifecycle"]').trigger('click');
    await flushPromises();

    expect(mocks.getMcpServerStatus).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain('start failed');
  });

  it('should show a loading state before the initial status resolves', async () => {
    mocks.getMcpServerStatus.mockReturnValueOnce(new Promise(() => {}));

    const wrapper = createWrapper();
    await nextTick();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.status.loading');
  });

  it('should show the desktop-only message outside Electron', async () => {
    mocks.isPackaged = false;

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.text()).toContain('backend_settings.settings.mcp_server.desktop_only');
    expect(mocks.getMcpServerStatus).not.toHaveBeenCalled();
  });
});
