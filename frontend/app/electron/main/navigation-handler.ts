import process from 'node:process';

export class NavigationHandler {
  private readonly isMac = process.platform === 'darwin';

  setupNavigationEvents(webContents: Electron.WebContents): void {
    webContents.on('before-input-event', (event, input) => {
      if (!this.shouldHandleNavigation(webContents, input)) {
        return;
      }

      this.handleKeyboardNavigation(webContents, input, event)
        .then()
        .catch(error => console.error(error));
    });
  }

  private isBackNavigation(input: Electron.Input): boolean {
    return input.key === '[' || input.key === 'ArrowLeft';
  }

  private isForwardNavigation(input: Electron.Input): boolean {
    return input.key === ']' || input.key === 'ArrowRight';
  }

  private async handleKeyboardNavigation(webContents: Electron.WebContents, input: Electron.Input, event: Electron.Event) {
    const canGoBack = webContents.navigationHistory.canGoBack();
    const canGoForward = webContents.navigationHistory.canGoForward();

    if (this.isBackNavigation(input) && canGoBack) {
      await this.handleNavigateBack(webContents, event, input);
    }

    if (this.isForwardNavigation(input) && canGoForward) {
      await this.handleNavigateForward(webContents, event, input);
    }
  }

  private shouldHandleNavigation(webContents: Electron.WebContents, input: Electron.Input): boolean {
    const isModifierPressed = this.isMac ? input.meta : input.alt;
    return isModifierPressed || !webContents.isFocused();
  }

  private async handleNavigateBack(webContents: Electron.WebContents, event: Electron.Event, input: Electron.Input) {
    if (input.key === '[' || !(await this.isInputFieldFocused(webContents))) {
      event.preventDefault();
      webContents.navigationHistory.goBack();
    }
  }

  private async handleNavigateForward(webContents: Electron.WebContents, event: Electron.Event, input: Electron.Input) {
    if (input.key === ']' || !(await this.isInputFieldFocused(webContents))) {
      event.preventDefault();
      webContents.navigationHistory.goForward();
    }
  }

  private async isInputFieldFocused(webContents: Electron.WebContents): Promise<boolean> {
    return webContents.executeJavaScript(`
      (function() {
        const activeElement = document.activeElement;
        
        // Check for text input elements
        const isTextInput = 
          activeElement.tagName === 'INPUT' ||
          activeElement.tagName === 'TEXTAREA' ||
          activeElement.isContentEditable ||
          activeElement.role === 'textbox' ||
          activeElement.closest('[contenteditable]'); // Check for nested contenteditable
        
        // Return early
        if (isTextInput) return true;
        
        // Check for any text selection
        const selection = window.getSelection();
        const hasTextSelection = selection.toString().length > 0;
        
        return hasTextSelection;
      })()
    `).catch(() => false);
  }
}
