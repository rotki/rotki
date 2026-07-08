import { beforeEach, describe, expect, it, vi } from 'vitest';

async function loadComposable(): Promise<typeof import('./use-report-issue')['useReportIssue']> {
  vi.resetModules();
  return (await import('./use-report-issue')).useReportIssue;
}

describe('useReportIssue', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('should start hidden with empty defaults', async () => {
    const useReportIssue = await loadComposable();
    const { initialDescription, initialTitle, visible } = useReportIssue();
    expect(get(visible)).toBe(false);
    expect(get(initialTitle)).toBe('');
    expect(get(initialDescription)).toBe('');
  });

  it('should populate title and description and become visible on show', async () => {
    const useReportIssue = await loadComposable();
    const { initialDescription, initialTitle, show, visible } = useReportIssue();
    show({ title: 'Broken', description: 'It fails' });
    expect(get(visible)).toBe(true);
    expect(get(initialTitle)).toBe('Broken');
    expect(get(initialDescription)).toBe('It fails');
  });

  it('should fall back to empty strings when show is called without a payload', async () => {
    const useReportIssue = await loadComposable();
    const { initialDescription, initialTitle, show, visible } = useReportIssue();
    show();
    expect(get(visible)).toBe(true);
    expect(get(initialTitle)).toBe('');
    expect(get(initialDescription)).toBe('');
  });

  it('should hide on close without clearing the stored payload', async () => {
    const useReportIssue = await loadComposable();
    const { close, initialTitle, show, visible } = useReportIssue();
    show({ title: 'Broken' });
    close();
    expect(get(visible)).toBe(false);
    expect(get(initialTitle)).toBe('Broken');
  });

  it('should share state across calls (shared composable)', async () => {
    const useReportIssue = await loadComposable();
    useReportIssue().show({ title: 'Shared' });
    expect(get(useReportIssue().initialTitle)).toBe('Shared');
  });
});
