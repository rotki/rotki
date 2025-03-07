import type { State } from 'electron-window-state';
import path from 'node:path';
import { screen } from 'electron';

interface ScreenDimensions {
  width: number;
  height: number;
  defaultWidth: number;
  defaultHeight: number;
  minimumWidth: number;
  minimumHeight: number;
}

export class WindowConfig {
  private readonly regularScreenWidth = 1366;
  private readonly regularScreenHeight = 768;
  private readonly minimumWidth = 1200;

  getScreenDimensions(): ScreenDimensions {
    const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

    const ratio = this.regularScreenWidth / this.minimumWidth;
    const minimumHeight = this.regularScreenHeight / ratio;

    return {
      width: screenWidth,
      height: screenHeight,
      minimumWidth: this.minimumWidth,
      minimumHeight,
      defaultWidth: Math.floor(Math.max(screenWidth / ratio, this.minimumWidth)),
      defaultHeight: Math.floor(Math.max(screenHeight / ratio, minimumHeight)),
    };
  }

  getWindowOptions(state: State): Electron.BrowserWindowConstructorOptions {
    return {
      x: state.x, // defaults to the middle of the screen if not specified
      y: state.y, // defaults to the middle of the screen if not specified
      width: state.width,
      height: state.height,
      webPreferences: {
        nodeIntegration: false,
        sandbox: true,
        contextIsolation: true,
        preload: path.join(import.meta.dirname, 'preload.js'),
      },
    };
  }
}
