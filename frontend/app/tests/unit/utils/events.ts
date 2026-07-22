export function createClipboardEvent(text: string): ClipboardEvent {
  const clipboardData = new DataTransfer();
  clipboardData.setData('text/plain', text);

  return new ClipboardEvent('paste', {
    bubbles: true,
    cancelable: true,
    clipboardData,
  });
}
