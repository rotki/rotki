// Nice overview for electron tests with the chai.should model:
// https://dzone.com/articles/write-automated-tests-for-electron-with-spectron-m

const {
    path, chai, Application, electronPath, waitAfterLoad, waitAfterSignup
} = require('./utils/setup')

const guid = () => {
    const s4 = () => Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1)
    return s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
}

describe('User Settings: Fiat', function () {
  this.timeout(100000);

  beforeEach(function () {
    this.app = new Application({
      path: electronPath,
      args: [path.join(__dirname, '../..')]
    });
      return this.app.start();
  });

  afterEach(function () {
    if (this.app && this.app.isRunning()) {
        return this.app.stop();
    }
  });

  it('Adding a fiat balance and see that it\'s properly updated', async function () {
    const username = guid()
    const password = process.env.PASSWORD
    const btcAddress = process.env.BTC_ADDRESS

    // wait for sign-in / create-new-account modal
    await this.app.client.waitForExist('.jconfirm-box-container', 5000).should.eventually.equal(true);

    // choose create-new-account
    await this.app.client.click('button.create-new-account')

    await waitAfterLoad.call(this)

    // fill values
    await this.app.client.addValue('#user_name_entry', username)
    await this.app.client.addValue('#password_entry', password)
    await this.app.client.addValue('#repeat_password_entry', password)

    // click create-new-account
    await this.app.client.waitForExist('.jconfirm-buttons>button', 5000)
    await this.app.client.click('.jconfirm-buttons>button')

    await waitAfterSignup.call(this)
    
    // open dropdown menu
    await this.app.client.click('li#user-dropdown.dropdown')

    // make sure dropdown menu is open
    await this.app.client.waitForExist('li.dropdown.open', 5000).should.eventually.equal(true)
    
    await this.app.client.execute(function () {
        // remove all modals
        $('.jconfirm').remove()
    })
    await this.app.client.click('li#user_settings_button')

    await this.app.client.execute(function () {
        $('body').css('overflow', 'scroll')
        $('#fiat_type_entry')[0].scrollIntoView()
    })
    await this.app.client.waitForExist('#fiat_balances_table td.dataTables_empty')

    await this.app.client.execute(function () {
        // remove all modals
        $('.jconfirm').remove()
        $('#fiat_type_entry').val('USD')
    })
    await this.app.client.addValue('#fiat_value_entry', 15)
    await this.app.client.click('#modify_fiat_button')


    await this.app.client.waitForExist('#fiat_balances_table td.sorting_1', 28000)

    await this.app.client.getText('#fiat_balances_table td').should.eventually.contain('USD')

    await this.app.client.getText('#fiat_balances_table td.sorting_1').should.eventually.equal('15.00')
  });

});
