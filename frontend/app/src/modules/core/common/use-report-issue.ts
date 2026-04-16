interface ReportIssuePayload {
  title?: string;
  description?: string;
}

export const useReportIssue = createSharedComposable(() => {
  const visible = ref<boolean>(false);
  const initialTitle = ref<string>('');
  const initialDescription = ref<string>('');

  function show(payload?: ReportIssuePayload): void {
    set(initialTitle, payload?.title ?? '');
    set(initialDescription, payload?.description ?? '');
    set(visible, true);
  }

  function close(): void {
    set(visible, false);
  }

  return {
    close,
    initialDescription,
    initialTitle,
    show,
    visible,
  };
});
