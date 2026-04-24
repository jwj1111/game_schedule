"""
爬虫基类：基于 Playwright + BeautifulSoup。
每个站点对应一个 parse_xxx 方法，通过 parser_registry 注册。

注意：本文件从原 info_crawl.py 迁移而来，核心逻辑保持一致；
仅做了「容器节点 None 守护」的小健壮性补丁，未改动抓取/解析流程。
"""

import time
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, Playwright


class BaseSpider:
    def __init__(self, ignore_https_errors: bool = False, headless: bool = True,
                 timeout: int = 15, retry_times: int = 3):
        """
        ignore_https_errors: 是否忽略 HTTPS 证书错误，内网/自签名证书站点传 True
        headless:            是否用无头模式，调试时可传 False 看浏览器界面
        timeout:             单次操作超时（秒）
        retry_times:         重试次数
        """
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        self.timeout = timeout
        self.retry_times = retry_times
        self.ignore_https_errors = ignore_https_errors
        self.headless = headless

        # 浏览器实例懒启动、复用
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

        # 网站名 -> 解析函数
        self.parser_registry = {
            "火影忍者": self.parse_huoying,
            "DNF": self.parse_dnf,
            "无畏契约": self.parse_valo,
            "王者荣耀世界": self.parse_wzrysj,
            "nba2kol2": self.parse_nba2kol2,
            "逆战": self.parse_nizhan,
            "QQ炫舞": self.parse_qqxuanwu,
            "三角洲行动": self.parse_sjzxd,
            "QQ飞车": self.parse_qqfeiche,
            "QQ炫舞2": self.parse_qqxuanwu2,
            "英雄联盟": self.parse_lol,
            "FIFAOnline4": self.parse_fifaonline4,
            "QQ三国": self.parse_qqsg,
            "金铲铲之战": self.parse_jcczz,
            "nba2kol": self.parse_nba2kol,
        }

    # ---------------- 浏览器周期 ----------------
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

    # ---------------- 网络请求 ----------------
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
                    page.wait_for_selector(wait_selector, timeout=self.timeout * 1000)
                else:
                    try:
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
                if context:
                    try:
                        context.close()
                    except Exception:
                        pass

        print(f"重试{self.retry_times}次依然失败: {url}")
        return None

    # ---------------- 解析器 ----------------
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
        if ul is None:
            return []

        items: List[Dict[str, Any]] = []
        for li in ul.select("li.list-item"):
            a = li.select_one("a")
            if not a:
                continue

            h5 = a.select_one("h5.item-title")
            if not h5:
                continue

            href = a.get("href", "").strip()

            item = self._empty_item(source="火影忍者")
            item["info"] = h5.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)

        return items

    def parse_dnf(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """DNF 解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("ul.news-list")
        if ul is None:
            return []

        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            span = a.select_one("span.newslist-tit")
            if not span:
                continue
            href = a.get("href", "").strip()

            item = self._empty_item(source="DNF")
            item["info"] = span.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)

        return items

    def parse_valo(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """无畏契约解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        div = soup.select_one("div.news-list")
        if div is None:
            return []

        items: List[Dict[str, Any]] = []
        for div_element in div.select("div.news-text"):
            news_title = div_element.select_one("p.news-title")
            if not news_title:
                continue
            a = div_element.select_one("div.news-details a")
            if not a:
                continue
            href = a.get("href", "").strip()

            item = self._empty_item(source="无畏契约")
            item["info"] = news_title.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)

        return items
    
    def parse_wzrysj(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """王者荣耀世界解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        div = soup.select_one("div.newslist")
        if div is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for div_element in div.select("div.list"):
            a = div_element.select_one("a")
            if not a:
                continue
            h3 = a.select_one("div.title h3")
            href = a.get("href", "").strip()

            item = self._empty_item(source="王者荣耀世界")
            item["info"] = h3.get_text(strip=True)
            item["link"] = href
            items.append(item)
        
        return items
    
    def parse_nba2kol2(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """nba2kol2解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("ul.news_list")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a:nth-of-type(2)")
            if not a:
                continue
            href = a.get("href", "").strip()

            item = self._empty_item(source="nba2kol2")
            item["info"] = a.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)
        
        return items

    def parse_nizhan(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """逆战解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.m_news_list ul")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("p a:nth-of-type(2)")
            if not a:
                continue
            href = a.get("href", "").strip()

            item = self._empty_item(source="逆战")
            item["info"] = a.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)
        
        return items

    def parse_qqxuanwu(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """qq炫舞解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.list_content ul")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "").strip()
            title = a.get("title", "").strip()

            item = self._empty_item(source="QQ炫舞")
            item["info"] = title
            item["href"] = urljoin(target_url, href)
            items.append(item)

        return items
    
    def parse_sjzxd(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """三角洲解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.newsbox ul")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "").strip()
            h2 = a.select_one("h2")

            item = self._empty_item(source="三角洲行动")
            item["info"] = h2.get_text(strip=True)
            item["link"] = href
            items.append(item)

        return items

    def parse_qqfeiche(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """qq飞车解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.newlist_ct ul.list_news")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("p a:nth-of-type(2)")
            if not a:
                continue
            href = a.get("href", "").strip()

            item = self._empty_item(source="QQ飞车")
            item["info"] = a.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)
        
        return items
    
    def parse_qqxuanwu2(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """qq炫舞2解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.centet_ulist ul.clearfix")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "").strip()
            title = a.get("title", "").strip()

            item = self._empty_item(source="QQ炫舞2")
            item["info"] = title
            item["link"] = urljoin(target_url, href)
            items.append(item)

        return items
    
    def parse_lol(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """英雄联盟解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.spage-left ul.news-type-list")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "").strip()

            item = self._empty_item(source="英雄联盟")
            item["info"] = a.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)
        
        return items
    
    def parse_fifaonline4(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """fifa online 4解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.main-wrap.fl ul.content.fl")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li.news-item"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "").strip()
            span = a.select_one("span.news-title.ellipsis")

            item = self._empty_item(source="FIFAOnline4")
            item["info"] = span.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)
        
        return items
    
    def parse_qqsg(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """qq三国解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.newslist ul")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "").strip()
            a_title = a.find_all(string=True, recursive=False)
            title = "".join(a_title).strip()

            item = self._empty_item(source="QQ三国")
            item["info"] = title
            item["link"] = urljoin(target_url, href)
            items.append(item)
        
        return items

    def parse_jcczz(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """金铲铲之战解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.news-container ul.news-list")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a")
            if not a:
                continue
            href = a.get("href", "").strip()
            span = a.select_one("span.title")

            item = self._empty_item(source="金铲铲之战")
            item["info"] = span.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)
        
        return items

    def parse_nba2kol(self, html: str, target_url: str) -> List[Dict[str, Any]]:
        """nba2kol解析逻辑"""
        soup = BeautifulSoup(html, "html.parser")
        ul = soup.select_one("div.rtsider2.yahei ul.new_list")
        if ul is None:
            return []
        
        items: List[Dict[str, Any]] = []
        for li in ul.select("li"):
            a = li.select_one("a:nth-of-type(2)")
            if not a:
                continue
            href = a.get("href", "").strip()

            item = self._empty_item(source="nba2kol")
            item["info"] = a.get_text(strip=True)
            item["link"] = urljoin(target_url, href)
            items.append(item)
        
        return items



    # ---------------- 主入口 ----------------
    def run(self, site_name: str, target_url: str) -> List[Dict[str, Any]]:
        """
        单次爬取入口
        args:
            site_name:  解析器名，需在 parser_registry 中注册
            target_url: 要爬取的 URL
        return:
            本次获取的结果列表
        """
        parser = self.parser_registry.get(site_name)
        if parser is None:
            supported = ", ".join(self.parser_registry.keys())
            print(f"解析器未知：{site_name}，当前支持：{supported}")
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
