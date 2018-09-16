// Nice overview for electron tests with the chai.should model:
// https://dzone.com/articles/write-automated-tests-for-electron-with-spectron-m

const {
    path, chai, Application, electronPath, waitAfterLoad, waitAfterSignup
} = require('./utils/setup')

const guid = () => {
    const s4 = () => Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1)
    return s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
}

describe('User Settings: Ethereum', function () {
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

  it('Going to the user settings, adding an ethereum account and looking at its balance', async function () {
    const username = guid()
    const password = process.env.PASSWORD
    const ethAddress = process.env.ETH_ADDRESS

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
        $('#account_entry')[0].scrollIntoView()
    })
    await this.app.client.waitForExist('#blockchain_per_asset_table_body td.dataTables_empty')

    await this.app.client.execute(function () {
        // remove all modals
        $('.jconfirm').remove()
    })
    // Make sure the modal is not there
    await this.app.client.addValue('#account_entry', ethAddress)
    await this.app.client.click('#add_account_button')


    await this.app.client.waitForExist('#blockchain_per_asset_table_body td.sorting_1', 20000)

    await this.app.client.getText('#blockchain_per_asset_table_body td').should.eventually.contain('ETH')

    await this.app.client.getText('#ethchain_per_account_table_body td').should.eventually.contain(ethAddress)

    await this.app.client.getText('#blockchain_per_asset_table_body td.sorting_1').should.eventually.satisfy(function(txt) {
          let number = parseInt(txt, 10);
          return number >= 0;
    });

    // now scroll to the tokens list
    await this.app.client.execute(function () {
        $('body').css('overflow', 'scroll')
        $('ul.ms-list')[0].scrollIntoView()
    })

    // get the list of available tokens
    const tokens = await this.app.client.getText('ul.ms-list li.ms-elem-selectable')
    await this.app.client.execute(function () {
        // click OMG token
        $('ul.ms-list li.ms-elem-selectable span').filter(function () { return $(this).html() == 'OMG'; }).click();
    })
    // check that the <li> has been selected
    await this.app.client.waitForExist('ul.ms-list li.ms-elem-selection.ms-selected')
    // check that OMG has been moved to the owned tokens column
    await this.app.client.getText('ul.ms-list li.ms-elem-selection.ms-selected').should.eventually.equal('OMG')
    // check that the ethchain per account table has an extra column
    await this.app.client.waitForExist('#ethchain_per_account_table > thead > tr > th:nth-child(4)', 20000);

    // check that OMG is now in the ETH accouns table
    await this.app.client.getText('#ethchain_per_account_table > thead > tr > th:nth-child(3)').should.eventually.equal('OMG')
    // check that the table has a value for the amount of OMG
    await this.app.client.getText('#ethchain_per_account_table_body > tr:nth-child(1) > td:nth-child(3)').should.eventually.satisfy(function(txt) {
          let number = parseInt(txt, 10);
          return number >= 0;
      });
  });
});
