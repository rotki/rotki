export function trimOnPaste(event: ClipboardEvent): string {
  event.preventDefault();
  const data = event.clipboardData;
  if (!data) {
    return '';
  }
  return data.getData('text').trim();
}
