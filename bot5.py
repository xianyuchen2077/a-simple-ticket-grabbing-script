from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
from selenium.common.exceptions import StaleElementReferenceException

# ===== 登录检测启发式函数 =====
COMMON_LOGIN_TEXTS = ["登录", "登 录", "登录/注册", "Sign in", "Sign In", "Sign in to", "Log in", "Log In", "Login", "Sign‑in"]
COMMON_LOGIN_URL_PARTS = ["login", "signin", "sign-in", "auth", "account", "accounts", "oauth"]


def needs_login(driver, timeout=5):
    """
    判断当前页面是否需要登录。
    返回 (bool, reason)。
    启发式检测：URL、密码输入框、登录文字、用户名/邮箱字段、是否存在头像/个人区。
    """
    try:
        url = (driver.current_url or "").lower()
    except Exception:
        url = ""

    # 1) URL 检查
    for part in COMMON_LOGIN_URL_PARTS:
        if part in url:
            return True, f"url contains '{part}'"

    # 2) 密码输入框（强信号）
    try:
        pw = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        if pw:
            return True, "found input[type=password]"
    except Exception:
        pass

    # 3) 登录按钮/链接文字
    try:
        btns = driver.find_elements(By.XPATH, "//button|//a|//input[@type='submit']|//input[@type='button']")
        for b in btns:
            try:
                text = (b.text or b.get_attribute("value") or b.get_attribute("innerText") or "").strip()
            except Exception:
                text = ""
            if not text:
                continue
            for key in COMMON_LOGIN_TEXTS:
                if key.lower() in text.lower():
                    return True, f"found button/link text '{text}'"
    except Exception:
        pass

    # 4) 常见用户名/邮箱字段
    try:
        suspects = driver.find_elements(By.XPATH,
            "//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'user')]|"
            "//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'user')]|"
            "//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'email')]|"
            "//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'email')]")
        if suspects:
            return True, "found username/email input"
    except Exception:
        pass

    # 5) 否定信号：用户头像/个人中心存在则通常已登录
    try:
        avatar_selectors = [
            "//img[contains(@alt,'avatar') or contains(@alt,'头像') or contains(@class,'avatar') or contains(@class,'profile') ]",
            "//*[contains(@aria-label,'account') or contains(@aria-label,'个人') or contains(@aria-label,'profile')]",
            "//*[contains(@title,'账号') or contains(@title,'个人') or contains(@title,'profile')]",
            "//*[contains(@class,'user') and (name()!='input')]"
        ]
        for sel in avatar_selectors:
            els = driver.find_elements(By.XPATH, sel)
            if els:
                return False, "found profile/avatar element"
    except Exception:
        pass

    # 6) 基于 body 文本做弱判断
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text[:3000].lower()
        for key in COMMON_LOGIN_TEXTS:
            if key.lower() in body_text:
                return True, f"body contains login text '{key}'"
    except Exception:
        pass

    return False, "no strong login indicators found"

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

def _venue_page_ready(driver):
    """判断场地页面是否已经完成基础加载。"""
    try:
        return bool(driver.find_elements(By.XPATH, "//div[contains(@class,'date-item')]") )
    except Exception:
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

def wait_for_verifybox_closed(driver, timeout=300, poll_interval=0.2):
    print("检测到安全验证时，等待你手动完成...")
    start = time.time()

    while time.time() - start < timeout:
        try:
            boxes = driver.find_elements(By.CSS_SELECTOR, ".verifybox")
            visible_boxes = [box for box in boxes if box.is_displayed()]
            if not visible_boxes:
                print("安全验证已完成，继续执行。")
                return True
        except Exception:
            print("安全验证已完成，继续执行。")
            return True

        time.sleep(poll_interval)

    print("等待安全验证超时，继续执行后续步骤。")
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
        # "18:00~20:00",
        # "16:00~18:00",
        "20:00~22:00",
        # "10:00~12:00",
        # "08:00~10:00",
        # "07:00~08:00",
    ]

    force_reload = not _venue_page_ready(driver)

    # ===== 开抢循环 =====
    for i in range(100):
        try:
            print(f"\n 第{i+1}次")

            # 仅在页面没加载出来或上次失败后刷新
            if force_reload:
                driver.execute_script("location.reload()")

                wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class,'date-item')]")
                ))

                force_reload = False
            else:
                print("页面已加载，跳过刷新")

            # 选第4天
            if not click_4th_date(driver, wait):
                force_reload = True
                continue

            # 等时间加载稳定
            if not wait_for_time_stable(driver):
                force_reload = True
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
                force_reload = True
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

            wait_for_verifybox_closed(driver)

            radio_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//input[@type='radio' and @value='d467ef62f7ca439fb2445e040a2ab977']/ancestor::span[contains(@class,'el-radio__input')]")
            ))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", radio_btn)
            try:
                ActionChains(driver).move_to_element(radio_btn).pause(0.03).click().perform()
            except Exception:
                driver.execute_script("arguments[0].click();", radio_btn)
            print("选择发票抬头")

            pay_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class,'qd1') and normalize-space(.)='去支付']")
            ))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", pay_btn)
            try:
                ActionChains(driver).move_to_element(pay_btn).pause(0.03).click().perform()
            except Exception:
                driver.execute_script("arguments[0].click();", pay_btn)
            print("点击去支付")

            wx_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//img[@alt='微信' and contains(@src,'wx.png') and @onclick=\"pay('0201')\"]")
            ))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", wx_btn)
            try:
                ActionChains(driver).move_to_element(wx_btn).pause(0.03).click().perform()
            except Exception:
                driver.execute_script("arguments[0].click();", wx_btn)
            print("点击微信支付")

            print("🎉 成功进入下单！")

            return True

        except Exception as e:
            print("⚠️ 异常:", e)
            force_reload = True
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
    time.sleep(0.1)

    # ⑤ 打印调试信息（一定要留）
    print("当前URL:", driver.current_url)
    print("页面标题:", driver.title)

    # ===== 在继续导航前检查是否需要登录 =====
    need, reason = needs_login(driver, timeout=5)
    print("需要登录:", need, "原因:", reason)
    if need:
        print("检测到需要登录，请在打开的浏览器中完成登录。等待登录中（最多 300s）...")
        max_wait = 300
        start_t = time.time()
        while time.time() - start_t < max_wait:
            time.sleep(2)
            try:
                need2, r2 = needs_login(driver, timeout=2)
            except Exception:
                need2, r2 = True, "error during check"
            if not need2:
                print("检测到已登录，继续执行。")
                break
        else:
            print("等待登录超时，继续执行（后续步骤可能因未登录失败）")

    success = navigate_to_venue(driver, wait)

    if not success:
        print("导航失败，退出")
        driver.quit()
        exit()

    # 开抢
    reserve_venue(driver, wait)

    input("按回车关闭...")
    driver.quit()