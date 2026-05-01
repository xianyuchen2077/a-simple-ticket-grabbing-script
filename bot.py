from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time


def open_chrome():
    chrome_options = Options()

    chrome_options.add_argument(r"--user-data-dir=C:\Users\xiany\AppData\Local\Google\Chrome\User Data")
    chrome_options.add_argument(r"--profile-directory=Default")

    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=chrome_options)

    wait = WebDriverWait(driver, 5)
    actions = ActionChains(driver)

    driver.get("https://www.sports.tsinghua.edu.cn/venue/index.html#/home")

    time.sleep(0.2)
    driver.refresh()
    # 诊断输出：打印当前 URL、标题和页面内容长度，便于判断是否正确导航
    time.sleep(0.8)
    try:
        print("✅ 已连接浏览器")
        print("当前 URL:", driver.current_url)
        print("页面标题:", driver.title)
        src = driver.page_source or ""
        print("页面源码长度:", len(src))
    except Exception as _e:
        print("⚠️ 读取页面信息时出错:", _e)

    return driver, wait, actions


# =========================
# 工具函数
# =========================

def normalize(t):
    return t.replace("-", "~").replace(" ", "").strip()


def get_active_date_text(driver):
    active_dates = driver.find_elements(By.XPATH, "//div[contains(@class,'date-item') and contains(@class,'active')]")
    if not active_dates:
        active_dates = driver.find_elements(By.XPATH, "//div[contains(@class,'date-item-active')]")
    if not active_dates:
        return ""
    return active_dates[0].text.strip()


def click_4th_date(driver, wait):
    wait.until(lambda d: len(d.find_elements(
        By.XPATH, "//div[contains(@class,'date-item')]"
    )) >= 4)

    old_active = get_active_date_text(driver)

    for attempt in range(1, 4):
        dates = driver.find_elements(By.XPATH, "//div[contains(@class,'date-item')]")

        if len(dates) < 4:
            print("⚠️ 日期数量不足4个")
            return False

        target_date = dates[3]
        target_text = target_date.text.strip()

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target_date)

        try:
            ActionChains(driver).move_to_element(target_date).pause(0.03).click().perform()
        except Exception:
            driver.execute_script("arguments[0].click();", target_date)

        print(f"📅 第{attempt}次点击第4个日期: {target_text}")

        try:
            wait.until(lambda d:
                "date-item-active" in d.find_elements(By.XPATH, "//div[contains(@class,'date-item')]")[3].get_attribute("class")
                or "active" in d.find_elements(By.XPATH, "//div[contains(@class,'date-item')]")[3].get_attribute("class")
            )
            new_active = get_active_date_text(driver)
            print(f"✅ 日期切换成功: {old_active} -> {new_active}")
            return True
        except Exception:
            time.sleep(0.2)

    print("⚠️ 日期点击失败")
    return False


def wait_for_time_stable(driver, timeout=6):
    start = time.time()
    last = ""

    while time.time() - start < timeout:
        times = driver.find_elements(By.XPATH, "//div[contains(@class,'time')]")
        sig = str(len(times))

        if sig == last and len(times) > 0:
            return True

        last = sig
        time.sleep(0.2)

    return False


# =========================
# 主程序
# =========================

if __name__ == "__main__":
    driver, wait, actions = open_chrome()

    # ===== 菜单导航 =====
    menu1 = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(@class,'card') and contains(.,'场地预约')]")
    ))
    actions.move_to_element(menu1).perform()
    time.sleep(0.3)

    menu2 = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(@class,'list') and .//div[text()='羽毛球']]")
    ))
    actions.move_to_element(menu2).perform()
    time.sleep(0.3)

    target = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//div[contains(@class,'list') and .//div[contains(@class,'text') and contains(.,'气膜馆羽毛球')]]")
    ))
    driver.execute_script("arguments[0].click();", target)

    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(@class,'date-item')]")
    ))

    print("✅ 已进入场地页面")

    # ===== 定时 =====
    TARGET_TIME = "07:59:59"

    while True:
        if time.strftime("%H:%M:%S") >= TARGET_TIME:
            break
        time.sleep(0.05)

    priority_times = [
        "18:00~20:00",
        "16:00~18:00",
        "20:00~22:00",
        "10:00~12:00",
        "08:00~10:00",
    ]

    # ===== 开抢 =====
    for i in range(100):
        try:
            print(f"\n🚀 第{i+1}次")

            driver.refresh()

            wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'date-item')]")
            ))

            if not click_4th_date(driver, wait):
                continue

            if not wait_for_time_stable(driver):
                continue

            sites = driver.find_elements(By.XPATH, "//div[contains(@class,'sites-item')]")

            selected = None

            for p in priority_times:
                for site in sites[:12]:
                    times = site.find_elements(
                        By.XPATH,
                        ".//div[contains(@class,'time') and not(contains(@class,'time-disabled'))]"
                    )
                    for t in times:
                        if normalize(t.text) == normalize(p):
                            selected = t
                            break
                    if selected:
                        break
                if selected:
                    break

            if not selected:
                print("❌ 没有匹配时间")
                continue

            driver.execute_script("arguments[0].click();", selected)

            reserve_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class,'btn') and contains(.,'预约')]")
            ))
            driver.execute_script("arguments[0].click();", reserve_btn)

            confirm_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[text()='确认']]")
            ))
            driver.execute_script("arguments[0].click();", confirm_btn)

            print("🎉 成功进入下单")
            break

        except Exception as e:
            print("⚠️ 异常:", e)
            time.sleep(0.2)