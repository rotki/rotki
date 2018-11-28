import {Application, SpectronClient} from 'spectron';
import * as electron from 'electron';
import * as path from 'path';

export const GLOBAL_TIMEOUT = 60_000;
export const METHOD_TIMEOUT = 20_000;

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

export async function logout(client: SpectronClient) {
    await client.click('#user-dropdown');
    await client.waitForVisible('#logout_button', METHOD_TIMEOUT);
    await client.click('#logout_button');

    await client.waitForVisible('.jconfirm', METHOD_TIMEOUT);
    await client.click('.jconfirm-buttons>button');
    await client.waitUntilTextExists('.jconfirm-title', 'Sign In', METHOD_TIMEOUT);
}

export async function login(client: SpectronClient, username: string, password: string) {
    await client.clearElement('#username_entry');
    await client.addValue('#username_entry', username);

    await client.clearElement('#password_entry');
    await client.addValue('#password_entry', password);

    await client.click('.jconfirm-buttons>button');

    await client.waitUntilTextExists('.jconfirm-title', 'Successful Sign In', METHOD_TIMEOUT);
    await client.click('.jconfirm-buttons>button');
    await client.waitForVisible('.jconfirm', METHOD_TIMEOUT, true);
}
