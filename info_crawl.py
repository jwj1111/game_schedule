import time
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, Browser, Playwright
from urllib.parse import urljoin


class BaseSpider:
    def __init__(self, ignore_https_errors: bool = False, headless: bool = True):
        """
        ignore_https_errors: 是否忽略 HTTPS 证书错误，内网/自签名证书站点传 True
        headless:            是否用无头模式，调试时可传 False 看浏览器界面
        """
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        
        self.timeout = 15          # 单次操作超时（秒）
        self.retry_times = 3       # 重试次数
        self.ignore_https_errors = ignore_https_errors
        self.headless = headless

        # 浏览器实例懒启动、复用
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

        # 网站名 -> 解析函数
        self.parser_registry = {
            "火影忍者": self.parse_huoying,
            "DNF":      self.parse_dnf,
            "无畏契约":  self.parse_thefinals,
        }

    # 浏览器周期
    def _ensure_browser(self) -> Browser:
        """按需启动浏览器并复用"""
        if self._browser is None:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=self.headless)
        return self._browser

    def close(self) -> None:
        """释放浏览器资源"""
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._browser = None
        self._pw = None

    # 支持 with BaseSpider() as spider: 
    def __enter__(self) -> "BaseSpider":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # 网络请求（playwright）
    def request_page(self, url: str, wait_selector: Optional[str] = None) -> Optional[str]:
        """
        通用页面请求：启动无头浏览器，等待 JS 渲染完成，返回完整 HTML。
        wait_selector: 可选，若传入则等待该选择器对应元素出现后再取 HTML
        """
        browser = self._ensure_browser()

        for i in range(self.retry_times):
            context = None
            try:
                context = browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    ignore_https_errors=self.ignore_https_errors,
                    extra_http_headers={"Accept-Language": self.headers["Accept-Language"]},
                )
                page = context.new_page()

                # goto: 跳转+等 DOM 就绪的总耗时上限（毫秒）
                page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

                # 等待指定元素（精确）或网络空闲（通用）
                if wait_selector:
                    # wait_for_selector: 等目标元素出现的最长时间（毫秒）
                    page.wait_for_selector(wait_selector, timeout=self.timeout * 1000)
                else:
                    try:
                        # networkidle: 等网络空闲的最长时间（毫秒）
                        page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                    except Exception:
                        # 部分站点长连接导致 networkidle 永远不触发，忽略继续取 HTML
                        pass

                html = page.content()
                print(f"页面获取成功: {url}")
                return html

            except Exception as e:
                print(f"页面获取失败，第{i+1}次重试: {url}, 错误: {e}")
                time.sleep(2 ** i)

            finally:
                # 关闭 context 回收页面资源，保留 browser
                if context:
                    try:
                        context.close()
                    except Exception:
                        pass

        print(f"重试{self.retry_times}次依然失败: {url}")
        return None

    # 解析器：每网站一方法
    @staticmethod
    def _empty_item(source: str) -> Dict[str, Any]:
        """统一字段模板"""
        return {
            "game": source,
            "info": "",
            "link": "",
        }

    def parse_huoying(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """火影忍者解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("ul.content-list")

        items = []

        for li in ul.select("li.list-item"):
            a = li.select_one("a")
            if not a:
                continue

            h5 = a.select_one("h5.item-title")

            href = a.get("href", "").strip()

            item = self._empty_item(source="火影忍者")
            item["info"] = h5.get_text(strip=True)
            # 路径拼接
            item["link"] = urljoin(target_url, href)

            items.append(item)

        return items

    def parse_dnf(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """DNF 解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("ul.news-list")

        items = []

        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            span = a.select_one("span.newslist-tit")
            href = a.get("href", "").strip()

            item = self._empty_item(source="DNF")
            item["info"] = span.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            # 路径拼接
            items.append(item)

        return items

    def parse_thefinals(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """无畏契约 解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        div = soup.select_one("div.news-list")

        items = []

        for div_element in div.select("div.news-text"):
            news_title = div_element.select_one("p.news-title")
            if not news_title:
                continue
            a = div_element.select_one("div.news-details a")
            href = a.get("href", "").strip()

            item = self._empty_item(source="无畏契约")
            item["info"] = news_title.get_text(strip=True)
            item["link"] = urljoin(target_url, href)

            items.append(item)

        return items

    # 主入口
    def run(self, site_name: str, target_url: str) -> List[Dict[str, Any]]:
        """
        爬虫主入口
        args:
            site_name:  网站名，需在 parser_registry 中注册
            target_url: 要爬取的 URL
        return:
            本次获取的结果列表
        """
        parser = self.parser_registry.get(site_name)
        if parser is None:
            supported = ", ".join(self.parser_registry.keys())
            print(f"网站名未知：{site_name}，当前支持：{supported}")
            return []

        html = self.request_page(target_url)
        if not html:
            return []

        try:
            items = parser(html, target_url)
        except Exception as e:
            print(f"解析异常 [{site_name}] {target_url}: {e}")
            return []

        if items:
            print(f"解析得到 {len(items)} 条: [{site_name}] {target_url}")
        else:
            print(f"解析结果为空: [{site_name}] {target_url}")
        return items


if __name__ == "__main__":
    # -------- 用法 1：基础单次调用 --------
    # spider = BaseSpider()
    # results = spider.run("火影忍者", "https://hy.163.com/")
    # print(results)
    # spider.close()

    # -------- 用法 2：推荐写法，用 with 自动释放资源 --------
    # with BaseSpider() as spider:
    #     results = spider.run("火影忍者", "https://hy.163.com/")
    #     print(results)

    # -------- 用法 3：批量爬多个站点，浏览器只启动一次 --------
    # tasks = [
    #     ("火影忍者", "https://hy.163.com/"),
    #     ("DNF",      "https://dnf.qq.com/"),
    #     ("无畏契约",  "https://valorant.qq.com/"),
    # ]
    # all_results = []
    # with BaseSpider() as spider:
    #     for site, url in tasks:
    #         all_results.extend(spider.run(site, url))
    # print(f"共抓到 {len(all_results)} 条")

    # -------- 用法 4：内网或自签名 HTTPS 站点 --------
    # 忽略证书错误（默认 False，严格校验）
    # with BaseSpider(ignore_https_errors=True) as spider:
    #     spider.run("火影忍者", "https://内网地址/")

    # -------- 用法 5：关掉无头模式，看浏览器行为 --------
    # headless=False 会弹出真实的 Chromium 窗口
    # with BaseSpider(headless=False) as spider:
    #     spider.run("火影忍者", "https://hy.163.com/")

    # -------- 用法 6：等待某个元素出现再取 HTML --------
    # 若站点的目标内容是懒加载，networkidle 可能不准，
    # 可以直接调用 request_page 并指定 wait_selector
    # with BaseSpider() as spider:
    #     html = spider.request_page(
    #         "https://hy.163.com/",
    #         wait_selector="li.list-item a",
    #     )
    #     items = spider.parse_huoying(html) if html else []
    #     print(items)

    # # -------- 示例1：跑火影 --------
    # with BaseSpider(ignore_https_errors=True) as spider:
    #     results = spider.run("火影忍者", "https://hyrz.qq.com/web202003/newsList.html")
    #     print("抓取结果:", results)

    # # -------- 示例2：跑dnf --------
    # with BaseSpider(ignore_https_errors=True) as spider:
    #     results = spider.run("DNF", "https://dnf.qq.com/webplat/info/news_version3/119/495/m22990/list_1.shtml")
    #     print("抓取结果:", results)

    # # -------- 示例3：跑无畏契约 --------
    # with BaseSpider(ignore_https_errors=True) as spider:
    #     results = spider.run("无畏契约", "https://val.qq.com/news.html?page=1&keyword=")
    #     print("抓取结果:", results)

    with BaseSpider() as spider:
        hy_rlst = spider.run("火影忍者", "https://hyrz.qq.com/web202003/newsList.html ")
        dnf_rlst = spider.run("DNF", "https://dnf.qq.com/webplat/info/news_version3/119/495/m22990/list_1.shtml")
        tf_rlst = spider.run("无畏契约", "https://val.qq.com/news.html?page=1&keyword=")

    all_rlst = hy_rlst + dnf_rlst + tf_rlst
    print(all_rlst)

    # import pandas as pd
    # df = pd.DataFrame(all_rlst)
    # df.to_excel("info.xlsx", index=False)
    # print("结果已保存至info.xlsx")

