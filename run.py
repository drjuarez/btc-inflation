from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
import time
import re
floats = re.compile("\d+\.\d+")


#  Control Plane
buy_btn_id = "addCartMain_addCartButton"
guest_form_path = "//form[@id='guestCheckoutForm']"
co_frame_path = "//iframe[@name='bongoCheckoutPage']"
co_btn_text = "Check Out"
guest_continue_btn_text = "Continue as Guest"
price_section_id = "priceSection"
billing_addr_id = "divBillingAddress"
shipping_id = "divShippingAddress"
ship_method_id = "divShippingMethod"
pmt_form_id = "divPayment"
driver = webdriver.Chrome()


#  Issues / TODO
# ------------------------------------------
#  - If items have additional selection
#  - Handle when an item runs out of stock
#  - Handle when the html page changes
#  - How to actually calculate inflation
#  - Do we need the price in SGD?
# ------------------------------------------

def get_sgd_price():
    span = driver.find_element_by_xpath("//div[@id='priceSection']//span[@class='monetary-price-value']")
    return span.get_attribute("content")


def add_to_cart():
    try:
        elem = driver.find_element_by_id(buy_btn_id)
    except Exception as e:
        print("ERROR: {} not found in dom: {}".format(buy_btn_id, e))
    elem.submit()


def select_co_btn():
    header = retry(driver.find_element_by_tag_name, "header")
    checkout_btn = retry(header.find_element_by_link_text, co_btn_text)

    if not checkout_btn:
        raise Exception("ERROR: could not get_prices -- could not find checkout button at ", co_btn_text)
    checkout_btn.click()
    return checkout_btn


def continue_as_guest(checkout_btn):
    guest_continue = retry(get_btn_by_text, guest_continue_btn_text, checkout_btn.click)
    guest_continue.click()


def get_btn_by_text(target_text):
    btns = driver.find_elements_by_tag_name("button")
    for btn in btns:
        if btn.text.lower() == target_text.lower():
            return btn

    raise NameError("{} text not found on any btns".format(target_text))


def fill_form():
    co_frame = retry(driver.find_element_by_xpath, co_frame_path)
    driver.switch_to.frame(co_frame)
    billform = retry(driver.find_element_by_id, "divBillingAddress")
    rows = billform.find_elements_by_tag_name("tr")
    for row in rows:
        cells = row.find_elements_by_tag_name("td")

        if "email" in cells[0].text.lower():
            input = row.find_element_by_tag_name("input")
            input.send_keys("email@email.com")

        elif "country" in cells[0].text.lower():
            option = cells[1].find_element_by_xpath("//option[@value='SG']")
            option.click()

        elif "phone" in cells[0].text.lower():
            inputs = row.find_elements_by_tag_name("input")
            inputs[1].send_keys("5555 5555")

        elif "zip" in cells[0].text.lower():
            inputs = row.find_elements_by_tag_name("input")
            inputs[0].send_keys("738343")

        else:
            try:
                input = row.find_element_by_tag_name("input")
                input.send_keys("some text")
            except:
                continue

    ship_form = driver.find_element_by_id(shipping_id)
    cb = ship_form.find_element_by_xpath("//input[@type='checkbox']")
    cb.click()

    method_form = driver.find_element_by_id(ship_method_id)
    rb = retry(method_form.find_elements_by_xpath, "//input[@type='radio']")
    retry(rb[1].click)


def scrape_price():
    pmt_form = driver.find_element_by_id(pmt_form_id)
    btc_option = retry(pmt_form.find_element_by_xpath, "//option[@value='bitcoin']")

    def get():
        btc_option.click()
        paylink = retry(pmt_form.find_element_by_id, "link-coinbase")
        pr = floats.findall(paylink.text)
        if len(pr) == 1:
            return pr[0]
        else:
            raise Exception("price not found")
    return retry(get)


def retry(fn, arg=None, on_fail=None, wait_seconds=10):
    for i in range(wait_seconds):
        try:
            if arg:
                res = fn(arg)
            else:
                res = fn()
            return res
        except:
            try:
                time.sleep(i)
                if on_fail:
                    on_fail()
            except StaleElementReferenceException:  # means we have progressed so try again
                continue
    print("could not find element at ", arg)
    return


urls = [
    # "https://www.overstock.com/Home-Garden/Carbon-Loft-Edelman-Black-Metal-and-Wood-Desk/22801600/product.html?recset=a286ed2d-a8f6-4555-a5a0-f8722cf11256&refccid=6VBSZP6JOHJ3S5CCEWBL6BQXQU&searchidx=0&recalg=63&recidx=0&kwds=computer%20desk&rfmt=",
    "https://www.overstock.com/Jewelry-Watches/Tag-Heuer-Mens-CAZ1014.BA0842-Formula-One-Chronograph-Stainless-Steel-Watch/15872745/product.html?refccid=EKZNMSEZC32ISF2NAPXFBI6SIQ&searchidx=0&kwds=&rfmt=brand%3ATag%20Heuer",
    # "https://www.overstock.com/Bedding-Bath/Truly-Soft-Pinch-Pleat-Solid-3-Piece-Comforter-Set/16079555/product.html?option=26751750&refccid=UFPUJYPPSUFL462CXHJR7PAEWU&searchidx=0&kwds=&rfmt=size%3ATwin%20XL"
]


prices = []
for url in urls:
    driver.get(url)
    sgd = get_sgd_price()
    add_to_cart()
    co = select_co_btn()
    continue_as_guest(co)
    fill_form()
    price = scrape_price()
    prices.append({
        "url": url,
        "btc": price,
        "sgd": sgd
    })

print(prices)
driver.close()
