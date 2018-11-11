import {Application, SpectronClient} from 'spectron';
import * as electron from 'electron';
import * as path from 'path';

export const GLOBAL_TIMEOUT = 60_000;
export const METHOD_TIMEOUT = 15_000;

export function initialiseSpectron() {

    return new Application({
        path: electron as any,
        args: [path.join(__dirname, '../..')],
        env: {
            ELECTRON_ENABLE_LOGGING: true,
            ELECTRON_ENABLE_STACK_DUMPING: true,
            NODE_ENV: 'development'
        },
        startTimeout: 10000,
        chromeDriverLogPath: '../chromedriverlog.txt'
    });
}

export async function createAccount(app: Application, username: string, password: string) {
    await app.client.waitForExist('.jconfirm-box-container', METHOD_TIMEOUT);

    await app.client.click('.jconfirm-buttons :nth-child(2)');

    await app.client.waitForExist('#repeat_password_entry', METHOD_TIMEOUT);

    await app.client.addValue('#user_name_entry', username);
    await app.client.addValue('#password_entry', password);
    await app.client.addValue('#repeat_password_entry', password);

    await app.client.click('.jconfirm-buttons>button');

    await app.client.waitUntilTextExists('div', `Welcome ${username}!`, METHOD_TIMEOUT);
    await app.client.waitUntilTextExists('div', `Welcome to Rotkehlchen!`, METHOD_TIMEOUT);

    await app.client.execute(() => {
        // noinspection JSJQueryEfficiency
        $('.jconfirm-buttons>button').click();
        // noinspection JSJQueryEfficiency
        $('.jconfirm-buttons>button').click();
    });

    await app.client.pause(50);

    await app.client.waitForVisible('.jconfirm', METHOD_TIMEOUT, true);
}

export async function navigateTo(client: SpectronClient, elementId: string) {
    await client.click('#user-dropdown');
    await client.waitForVisible(elementId, METHOD_TIMEOUT);
    await client.click(elementId);
    await client.pause(100);
}

export async function closeAddYourSettingsPopup(client: SpectronClient) {
    await client.waitUntilTextExists('.jconfirm-title', 'Add your settings', METHOD_TIMEOUT);
    await client.click('.jconfirm-buttons>button');
}

export async function navigateToUserSettings(client: SpectronClient) {
    await client.click('#user-dropdown');
    await client.waitForVisible('#user_settings_button', 5000);
    await client.click('#user_settings_button');
    await client.pause(100);
}

export async function closeAddYourSettingsPopup(client: SpectronClient) {
    await client.waitUntilTextExists('.jconfirm-title', 'Add your settings', 5000);
    await client.click('.jconfirm-buttons>button');
}
