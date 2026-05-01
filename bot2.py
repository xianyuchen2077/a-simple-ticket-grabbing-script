from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
from selenium.common.exceptions import StaleElementReferenceException

def open_chrome():
    chrome_options = Options()

    # 使用你复制的用户数据
    chrome_options.add_argument(r"--user-data-dir=C:\Users\xiany\Desktop\Venue_reservation_booking_bot\chrome_auto")

    # 指定配置
    chrome_options.add_argument(r"--profile-directory=Default")

    # 可选（防一些报错）
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    wait = WebDriverWait(driver, 5)

    return driver, wait

def navigate_to_venue(driver, wait):

    print("开始导航到场地页面...")

    time.sleep(0.05)  # 等页面渲染（关键）
    actions = ActionChains(driver)

    try:
        # ===== 菜单导航 =====
        menu1 = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'card') and contains(.,'场地预约')]")
        ))
        actions.move_to_element(menu1).perform()
        time.sleep(0.05)

        menu2 = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'list') and .//div[text()='羽毛球']]")
        ))
        actions.move_to_element(menu2).perform()
        time.sleep(0.05)

        target = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class,'list') and .//div[contains(@class,'text') and contains(.,'气膜馆羽毛球')]]")
        ))
        driver.execute_script("arguments[0].click();", target)

        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'date-item')]")
        ))

        print("已进入场地页面")
        return True

    except Exception as e:
        print("导航失败:", e)
        return False

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
    # 等待至少 4 个日期元素出现
    wait.until(EC.presence_of_all_elements_located(
        (By.XPATH, "//div[contains(@class,'date-item')]")
    ))

    old_active = get_active_date_text(driver)

    dates = driver.find_elements(By.XPATH, "//div[contains(@class,'date-item')]")
    if len(dates) < 4:
        print("⚠️ 日期数量不足4个")
        return False

    target_date = dates[3]
    target_text = target_date.text.strip()

    # 滚动到中间并尝试点击（先用 ActionChains）
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target_date)
    try:
        ActionChains(driver).move_to_element(target_date).pause(0.03).click().perform()
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", target_date)
        except Exception:
            print("⚠️ 点击日期时发生异常，尝试继续等待状态变化")

    print(f"点击第4个日期: {target_text}")

    # 等待页面短暂加载：先轮询最多 1.5s，若已生效则直接返回，避免直接重试导致错误
    start_t = time.time()
    while time.time() - start_t < 1.5:
        if _is_date_active(driver, 3):
            new_active = get_active_date_text(driver)
            print(f"点击即时生效: {old_active} -> {new_active}")
            return True
        time.sleep(0.05)

    # 连续快速重试（每次点击后短轮询是否切换成功）
    for quick_try in range(5):
        try:
            ActionChains(driver).move_to_element(target_date).pause(0.02).click().perform()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", target_date)
            except Exception:
                pass

        # 短时间内轮询检查是否切换为 active
        for _ in range(6):
            if _is_date_active(driver, 3):
                new_active = get_active_date_text(driver)
                print(f"快速重试成功 (attempt {quick_try+1}): {old_active} -> {new_active}")
                return True
            time.sleep(0.05)

    print("⚠️ 日期点击失败")
    return False


def _is_date_active(driver, index):
    """检查索引为 index 的日期元素是否包含 active 类。index 为 0 基准。"""
    try:
        elems = driver.find_elements(By.XPATH, "//div[contains(@class,'date-item')]")
        if len(elems) <= index:
            return False
        cls = elems[index].get_attribute('class') or ''
        return 'active' in cls or 'date-item-active' in cls
    except StaleElementReferenceException:
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
        # time.sleep(0.1)
        time.sleep(0.05)

    return False

def reserve_venue(driver, wait):
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    print("等待抢票时间...")

    TARGET_TIME = "07:59:00"

    # ===== 定时 =====
    while True:
        if time.strftime("%H:%M:%S") >= TARGET_TIME:
            break
        time.sleep(0.01)

    print("开始抢！")

    # ===== 时间优先级 =====
    priority_times = [
        "18:00~20:00",
        "16:00~18:00",
        "20:00~22:00",
        "10:00~12:00",
        "08:00~10:00",
        # "07:00~08:00",
    ]

    # ===== 开抢循环 =====
    for i in range(2):
        try:
            print(f"\n 第{i+1}次")

            # 用 JS 刷新更快
            driver.execute_script("location.reload()")

            wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'date-item')]")
            ))

            # 选第4天
            if not click_4th_date(driver, wait):
                continue

            # 等时间加载稳定
            if not wait_for_time_stable(driver):
                continue

            sites = driver.find_elements(By.XPATH, "//div[contains(@class,'sites-item')]")

            selected = None

            # ===== 按优先级选时间 =====
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
                print("没有匹配时间")
                continue

            print("找到时间:", selected.text)

            # 点击时间
            driver.execute_script("arguments[0].click();", selected)
            print("选择时间")

            # 点击预约（先等待可见、滚动到中心，再用 ActionChains 点击；失败时回退到 JS 或派发 MouseEvent）
            reserve_btn = wait.until(EC.visibility_of_element_located(
                (By.XPATH, "//div[contains(@class,'btn') and contains(.,'预约')]")
            ))
            # 确保元素在视口中间
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", reserve_btn)
            try:
                ActionChains(driver).move_to_element(reserve_btn).pause(0.03).click().perform()
            except Exception:
                # 回退到 JS 点击
                try:
                    driver.execute_script("arguments[0].click();", reserve_btn)
                except Exception:
                    # 最后回退：派发一个原生 MouseEvent
                    driver.execute_script(
                        "var el=arguments[0]; el.scrollIntoView({block:'center'}); var ev=new MouseEvent('click', {bubbles:true,cancelable:true,view:window}); el.dispatchEvent(ev);",
                        reserve_btn
                    )
            print("点击预约")

            # 点击确认
            confirm_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[text()='确认']]")
            ))
            driver.execute_script("arguments[0].click();", confirm_btn)
            print("点击确认")

            print("🎉 成功进入下单！")

            return True

        except Exception as e:
            print("⚠️ 异常:", e)
            time.sleep(0.1)

    print("抢票失败")
    return False

if __name__ == "__main__":
    driver, wait = open_chrome()

    print("Chrome 已启动")

    # ① 先进入主页面（非常重要）
    driver.get("https://www.sports.tsinghua.edu.cn/venue/index.html")

    # ② 等浏览器加载
    time.sleep(0.2)

    # ③ 强制切换前端路由（核心）
    driver.execute_script("window.location.hash = '#/home'")

    # ④ 再等前端渲染
    time.sleep(0.05)

    # ⑤ 打印调试信息（一定要留）
    print("当前URL:", driver.current_url)
    print("页面标题:", driver.title)

    success = navigate_to_venue(driver, wait)

    if not success:
        print("导航失败，退出")
        driver.quit()
        exit()

    # 开抢
    reserve_venue(driver, wait)

    input("按回车关闭...")
    driver.quit()