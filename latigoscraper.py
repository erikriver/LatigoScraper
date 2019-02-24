from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
import datetime
import re


class Provider:
    def __init__(self, username, password, driver="firefox", driver_path=None):
        self.username = username
        self.password = password

        if driver.lower() == "firefox":
            self.driver = webdriver.Firefox()
        elif driver.lower() == "chrome":
            self.driver = webdriver.Chrome()

        self.accounts = []

    def login_to_account_home(self):
        """
        Gets the driver from the homepage (set in your __init__ override using
        self.homepage) to the very first page you are shown after logging in.
        """
        raise NotImplementedError

    def back_to_account_home(self):
        """
        Gets the driver back to account_home no matter where the other methods
        have taken it on the website.
        """
        raise NotImplementedError

    def get_transactions(self):
        """
        Retrieves latest transactions starting at account_home.
        """
        raise NotImplementedError

    def wait_until(self, callback, timeout=10):
        """
        Helper function that blocks the execution of the tests until the
        specified callback returns a value that is not falsy. This function can
        be called, for example, after clicking a link or submitting a form.
        See the other public methods that call this function for more details.
        """
        from selenium.webdriver.support.wait import WebDriverWait
        WebDriverWait(self.driver, timeout).until(callback)


class Account:
    def __init__(self, acc_name):
        self.acc_name = acc_name
        self.transactions = []


class Transaction:
    def __init__(self, tr_date, tr_desc, tr_amount):
        self.tr_date = tr_date
        self.tr_desc = tr_desc
        self.tr_amount = tr_amount

        if type(tr_date) is not datetime.datetime:
            raise TypeError('tr_date should be datetime.datetime')
        if type(tr_desc) is not str:
            raise TypeError('tr_desc should be string')
        if type(tr_amount) is not float:
            raise TypeError('tr_amount should be float')


class HSBC(Provider):
    def __init__(self, username, password, driver="firefox", driver_path=None):
        super().__init__(username, password, driver, driver_path)
        self.homepage = "https://www.hsbc.com.mx/acceso-banca/"
        self.driver.implicitly_wait(8)  # TODO: Use explicit waits instead to improve performance

    def login_to_account_home(self):
        self.driver.get(self.homepage)

        # Click on the Log On button
        link = self.driver.find_element_by_xpath('//*[@id="content_intro_button_1"]')
        link.click()

        # Enter username and click on Continue
        txt_username = self.driver.find_element_by_xpath('//*[@id="username"]')
        txt_username.send_keys(self.username)
        link = self.driver.find_element_by_xpath('//*[@id="formSubmitButton"]')
        link.click()

        # Click "Without Secure Key" button
        link = self.driver.find_element_by_xpath('//*[@id="innerPage"]/div/div/div/div/div/div[2]/ul/li[2]/a')
        link.click()

        # Enter password
        pwd_fields = self.driver.find_elements_by_css_selector('input[id^="pass"]')
        for field in pwd_fields:
            field_type = field.get_attribute('type')
            name = field.get_attribute('name')
            enabled = field.is_enabled()
            name_match = re.match(r'pass([1-8])', name)
            if name_match and field_type == 'password' and enabled:
                pass_idx = int(name_match.group(1)) - 1
                field.send_keys(self.password[pass_idx])

        # Log in
        link = self.driver.find_element_by_xpath('//*[@id="dijit_form_Form_0"]/div[3]/div/div/span/input')
        link.click()

    def back_to_account_home(self):
        self.driver.get('https://www.hsbc.co.uk/1/3/personal/online-banking')

    def get_transactions(self):

        today = datetime.datetime.now()

        self.wait_until(
            ec.element_to_be_clickable(
                (By.XPATH, '//*[@class="row accordionContainer accBundleContainer"]//*[@class="itemTitle"]')
            )
        )

        accounts = self.driver.find_elements_by_xpath(
            '//*[@class="row accordionContainer accBundleContainer"]//*[@class="itemTitle"]')
        no_of_accounts = len(accounts)

        for i in range(0, no_of_accounts):
            lnk_account = accounts[i]
            account_name = lnk_account.text
            account = Account(account_name)
            lnk_account.click()

            # Get to the earliest transactions:
            btn_search = self.driver.find_element_by_xpath('//*[@id="filterPayment_Show_Hide"][@title="Search"]')
            btn_search.click()

            self.wait_until(
                ec.text_to_be_present_in_element(
                    (By.XPATH, '//*[@data-dojo-attach-point="_dateDisclaimer"]'),
                    "The earliest date you can view"
                )
            )

            el_earliest = self.driver.find_element_by_xpath('//*[@data-dojo-attach-point="_dateDisclaimer"]')
            txt_earliest = el_earliest.text
            re_earliest = re.search(r'The earliest date you can view is (.+?)\.', txt_earliest).group(1)
            dt_earliest = datetime.datetime.strptime(re_earliest, '%d %b %Y')

            from_date = self.driver.find_element_by_xpath('//*[contains(@aria-labelledby, "dateFrom")]')
            from_date.clear()
            from_date.send_keys(dt_earliest.strftime('%d/%m/%Y'))

            to_date = self.driver.find_element_by_xpath('//*[contains(@aria-labelledby, "dateTo")]')
            to_date.clear()
            to_date.send_keys(today.strftime('%d/%m/%Y'))

            btn_view_results = self.driver.find_element_by_xpath('//*[@data-dojo-attach-point="dapViewResults"]')
            btn_view_results.click()

            # Show all the transactions on one page as far back as the website allows
            earliest = False
            while not earliest:
                btn_view_more = self.driver.find_element_by_xpath('//*[@id="_dapViewMore"]')
                hidden = btn_view_more.get_attribute('aria-hidden')
                if hidden == "true":
                    earliest = True
                else:
                    btn_view_more.click()

            rows = self.driver.find_elements_by_xpath('//*[@data-dojo-attach-point="bodyNode"]/div/table/tbody/tr')

            # Write transactions to Account object created earlier
            for row in rows:

                fields = row.find_elements_by_tag_name('td')

                td_date = datetime.datetime.strptime(fields[0].text.strip(), '%d %b %y')
                td_desc = fields[1].find_element_by_class_name('payeeItem0').text.strip()
                td_amount = float(fields[2].text.strip().replace(',', ''))

                account.transactions.append(Transaction(td_date, td_desc, td_amount))

            self.accounts.append(account)


class Banregio(Provider):
    def __init__(self, username, password, driver="firefox", driver_path=None):
        super().__init__(username, password, driver, driver_path)
        self.homepage = "https://www.banregio.com/"
        self.driver.implicitly_wait(8)  # TODO: Use explicit waits instead to improve performance

    def login_to_account_home(self):

        self.driver.get(self.homepage)

        txt_usu_clave = self.driver.find_element_by_xpath('//*[@id="Usu_Clave"]')
        txt_usu_clave.clear()
        txt_usu_clave.send_keys(self.username)
        txt_password = self.driver.find_element_by_xpath("frmLogin:strCustomerLogin_pwd")
        txt_password.clear()
        txt_password.send_keys(self.password)
        btn_submit = self.driver.find_element_by_name("frmLogin:btnLogin1")
        btn_submit.click()

    def back_to_account_home(self):
        btn_home = self.driver.find_element_by_name('ifCommercial:ifCustomerBar:outputLinkNavHome')
        btn_home.click()

    def get_transactions(self):
        accounts = self.driver.find_elements_by_xpath('//*[@class="account-name"]/a')
        no_of_accounts = len(accounts)
        for i in range(0, no_of_accounts):

            account = self.driver.find_element_by_xpath('//*[@class="account-name"]/a[{0}]'.format(i + 1))
            account_name = account.text
            self.accounts[account_name] = []
            account.click()

            # Go back to the earliest page of transactions
            earliest = False
            while not earliest:
                btn_earlier = self.driver.find_element_by_id('lnkEarlierBtnMACC')
                disabled = btn_earlier.get_attribute('disabled')
                if disabled == "true":
                    earliest = True
                else:
                    btn_earlier.click()

            latest = False
            while not latest:
                rows = self.driver.find_elements_by_xpath('//*[@class="transaction-details filter_-"]/tr')
                # for row in rows:
                #     columns = row.find_elements_by_tag_name('td')
                #     td_date = datetime.datetime.strptime(columns[0].text, '%d %b %y')
                #     td_desc = columns[1].text
                #     td_balance =
                #     self.accounts[account_name].append((td_date, td_type, td_desc, td_paid_out, td_paid_in, td_balance))
