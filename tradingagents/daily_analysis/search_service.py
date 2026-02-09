# -*- coding: utf-8 -*-
"""
===================================
A股自選股智能分析系統 - 搜尋服務模組
===================================

職責：
1. 提供統一的新聞搜尋介面
2. 支援 Tavily 和 SerpAPI 兩種搜尋引擎
3. 多 Key 負載均衡和故障轉移
4. 搜尋結果快取和格式化
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from itertools import cycle
import requests
from newspaper import Article, Config

logger = logging.getLogger(__name__)


def fetch_url_content(url: str, timeout: int = 5) -> str:
    """
    獲取 URL 網頁正文內容 (使用 newspaper3k)
    """
    try:
        # 設定 newspaper3k
        config = Config()
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        config.request_timeout = timeout
        config.fetch_images = False  # 不下載圖片
        config.memoize_articles = False # 不快取

        article = Article(url, config=config, language='zh') # 預設中文，但也支援其他
        article.download()
        article.parse()

        # 獲取正文
        text = article.text.strip()

        # 簡單的後處理，去除空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        return text[:1500]  # 限制返回長度（比 bs4 稍微多一點，因為 newspaper 解析更乾淨）
    except Exception as e:
        logger.debug(f"Fetch content failed for {url}: {e}")

    return ""


@dataclass
class SearchResult:
    """搜尋結果資料類別"""
    title: str
    snippet: str  # 摘要
    url: str
    source: str  # 來源網站
    published_date: Optional[str] = None
    
    def to_text(self) -> str:
        """轉換為文字格式"""
        date_str = f" ({self.published_date})" if self.published_date else ""
        return f"【{self.source}】{self.title}{date_str}\n{self.snippet}"


@dataclass 
class SearchResponse:
    """搜尋回應"""
    query: str
    results: List[SearchResult]
    provider: str  # 使用的搜尋引擎
    success: bool = True
    error_message: Optional[str] = None
    search_time: float = 0.0  # 搜尋耗時（秒）
    
    def to_context(self, max_results: int = 5) -> str:
        """將搜尋結果轉換為可用於 AI 分析的上下文"""
        if not self.success or not self.results:
            return f"搜尋 '{self.query}' 未找到相關結果。"
        
        lines = [f"【{self.query} 搜尋結果】（來源：{self.provider}）"]
        for i, result in enumerate(self.results[:max_results], 1):
            lines.append(f"\n{i}. {result.to_text()}")
        
        return "\n".join(lines)


class BaseSearchProvider(ABC):
    """搜尋引擎基類"""
    
    def __init__(self, api_keys: List[str], name: str):
        """
        初始化搜尋引擎
        
        Args:
            api_keys: API Key 列表（支援多個 key 負載均衡）
            name: 搜尋引擎名稱
        """
        self._api_keys = api_keys
        self._name = name
        self._key_cycle = cycle(api_keys) if api_keys else None
        self._key_usage: Dict[str, int] = {key: 0 for key in api_keys}
        self._key_errors: Dict[str, int] = {key: 0 for key in api_keys}
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_available(self) -> bool:
        """檢查是否有可用的 API Key"""
        return bool(self._api_keys)
    
    def _get_next_key(self) -> Optional[str]:
        """
        獲取下一個可用的 API Key（負載均衡）
        
        策略：輪詢 + 跳過錯誤過多的 key
        """
        if not self._key_cycle:
            return None
        
        # 最多嘗試所有 key
        for _ in range(len(self._api_keys)):
            key = next(self._key_cycle)
            # 跳過錯誤次數過多的 key（超過 3 次）
            if self._key_errors.get(key, 0) < 3:
                return key
        
        # 所有 key 都有問題，重置錯誤計數並返回第一個
        logger.warning(f"[{self._name}] 所有 API Key 都有錯誤記錄，重置錯誤計數")
        self._key_errors = {key: 0 for key in self._api_keys}
        return self._api_keys[0] if self._api_keys else None
    
    def _record_success(self, key: str) -> None:
        """記錄成功使用"""
        self._key_usage[key] = self._key_usage.get(key, 0) + 1
        # 成功後減少錯誤計數
        if key in self._key_errors and self._key_errors[key] > 0:
            self._key_errors[key] -= 1
    
    def _record_error(self, key: str) -> None:
        """記錄錯誤"""
        self._key_errors[key] = self._key_errors.get(key, 0) + 1
        logger.warning(f"[{self._name}] API Key {key[:8]}... 錯誤計數: {self._key_errors[key]}")
    
    @abstractmethod
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """執行搜尋（子類實現）"""
        pass
    
    def search(self, query: str, max_results: int = 5, days: int = 7) -> SearchResponse:
        """
        執行搜尋
        
        Args:
            query: 搜尋關鍵詞
            max_results: 最大返回結果數
            days: 搜尋最近幾天的時間範圍（預設7天）
            
        Returns:
            SearchResponse 物件
        """
        api_key = self._get_next_key()
        if not api_key:
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=f"{self._name} 未配置 API Key"
            )
        
        start_time = time.time()
        try:
            response = self._do_search(query, api_key, max_results, days=days)
            response.search_time = time.time() - start_time
            
            if response.success:
                self._record_success(api_key)
                logger.info(f"[{self._name}] 搜尋 '{query}' 成功，返回 {len(response.results)} 條結果，耗時 {response.search_time:.2f}s")
            else:
                self._record_error(api_key)
            
            return response
            
        except Exception as e:
            self._record_error(api_key)
            elapsed = time.time() - start_time
            logger.error(f"[{self._name}] 搜尋 '{query}' 失敗: {e}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=str(e),
                search_time=elapsed
            )


class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily 搜尋引擎
    
    特點：
    - 專為 AI/LLM 優化的搜尋 API
    - 免費版每月 1000 次請求
    - 返回結構化的搜尋結果
    
    文件：https://docs.tavily.com/
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Tavily")
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """執行 Tavily 搜尋"""
        try:
            from tavily import TavilyClient
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="tavily-python 未安裝，請執行: pip install tavily-python"
            )
        
        try:
            client = TavilyClient(api_key=api_key)
            
            # 執行搜尋（優化：使用 advanced 深度、限制最近幾天）
            response = client.search(
                query=query,
                search_depth="advanced",  # advanced 獲取更多結果
                max_results=max_results,
                include_answer=False,
                include_raw_content=False,
                days=days,  # 搜尋最近天數的內容
            )
            
            # 記錄原始回應到日誌
            logger.info(f"[Tavily] 搜尋完成，query='{query}', 返回 {len(response.get('results', []))} 條結果")
            logger.debug(f"[Tavily] 原始回應: {response}")
            
            # 解析結果
            results = []
            for item in response.get('results', []):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=item.get('content', '')[:500],  # 截取前 500 字
                    url=item.get('url', ''),
                    source=self._extract_domain(item.get('url', '')),
                    published_date=item.get('published_date'),
                ))
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            # 檢查是否為配額問題
            if 'rate limit' in error_msg.lower() or 'quota' in error_msg.lower():
                error_msg = f"API 配額已用盡: {error_msg}"
            
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """從 URL 提取域名作為來源"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or '未知來源'
        except:
            return '未知來源'


class SerpAPISearchProvider(BaseSearchProvider):
    """
    SerpAPI 搜尋引擎
    
    特點：
    - 支援 Google、Bing、百度等多種搜尋引擎
    - 免費版每月 100 次請求
    - 返回真實的搜尋結果
    
    文件：https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "SerpAPI")
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """執行 SerpAPI 搜尋"""
        try:
            from serpapi import GoogleSearch
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="google-search-results 未安裝，請執行: pip install google-search-results"
            )
        
        try:
            # 確定時間範圍參數 tbs
            tbs = "qdr:w"  # 預設一週
            if days <= 1:
                tbs = "qdr:d"  # 過去 24 小時
            elif days <= 7:
                tbs = "qdr:w"  # 過去一週
            elif days <= 30:
                tbs = "qdr:m"  # 過去一月
            else:
                tbs = "qdr:y"  # 過去一年

            # 使用 Google 搜尋 (獲取 Knowledge Graph, Answer Box 等)
            params = {
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "google_domain": "google.com.hk", # 使用香港 Google，中文支援較好
                "hl": "zh-tw",  # 繁體中文介面
                "gl": "tw",     # 台灣地區偏好
                "tbs": tbs,     # 時間範圍限制
                "num": max_results # 請求的結果數量，注意：Google API 有時不嚴格遵守
            }
            
            search = GoogleSearch(params)
            response = search.get_dict()
            
            # 記錄原始回應到日誌
            logger.debug(f"[SerpAPI] 原始回應 keys: {response.keys()}")
            
            # 解析結果
            results = []
            
            # 1. 解析 Knowledge Graph (知識圖譜)
            kg = response.get('knowledge_graph', {})
            if kg:
                title = kg.get('title', '知識圖譜')
                desc = kg.get('description', '')
                
                # 提取額外屬性
                details = []
                for key in ['type', 'founded', 'headquarters', 'employees', 'ceo']:
                    val = kg.get(key)
                    if val:
                        details.append(f"{key}: {val}")
                        
                snippet = f"{desc}\n" + " | ".join(details) if details else desc
                
                results.append(SearchResult(
                    title=f"[知識圖譜] {title}",
                    snippet=snippet,
                    url=kg.get('source', {}).get('link', ''),
                    source="Google Knowledge Graph"
                ))
                
            # 2. 解析 Answer Box (精選回答/行情卡片)
            ab = response.get('answer_box', {})
            if ab:
                ab_title = ab.get('title', '精選回答')
                ab_snippet = ""
                
                # 財經類回答
                if ab.get('type') == 'finance_results':
                    stock = ab.get('stock', '')
                    price = ab.get('price', '')
                    currency = ab.get('currency', '')
                    movement = ab.get('price_movement', {})
                    mv_val = movement.get('percentage', 0)
                    mv_dir = movement.get('movement', '')
                    
                    ab_title = f"[行情卡片] {stock}"
                    ab_snippet = f"價格: {price} {currency}\n漲跌: {mv_dir} {mv_val}%"
                    
                    # 提取表格資料
                    if 'table' in ab:
                        table_data = []
                        for row in ab['table']:
                            if 'name' in row and 'value' in row:
                                table_data.append(f"{row['name']}: {row['value']}")
                        if table_data:
                            ab_snippet += "\n" + "; ".join(table_data)
                            
                # 普通文字回答
                elif 'snippet' in ab:
                    ab_snippet = ab.get('snippet', '')
                    list_items = ab.get('list', [])
                    if list_items:
                        ab_snippet += "\n" + "\n".join([f"- {item}" for item in list_items])
                
                elif 'answer' in ab:
                    ab_snippet = ab.get('answer', '')
                    
                if ab_snippet:
                    results.append(SearchResult(
                        title=f"[精選回答] {ab_title}",
                        snippet=ab_snippet,
                        url=ab.get('link', '') or ab.get('displayed_link', ''),
                        source="Google Answer Box"
                    ))

            # 3. 解析 Related Questions (相關問題)
            rqs = response.get('related_questions', [])
            for rq in rqs[:3]: # 取前 3 個
                question = rq.get('question', '')
                snippet = rq.get('snippet', '')
                link = rq.get('link', '')
                
                if question and snippet:
                     results.append(SearchResult(
                        title=f"[相關問題] {question}",
                        snippet=snippet,
                        url=link,
                        source="Google Related Questions"
                     ))

            # 4. 解析 Organic Results (自然搜尋結果)
            organic_results = response.get('organic_results', [])

            for item in organic_results[:max_results]:
                link = item.get('link', '')
                snippet = item.get('snippet', '')

                # 增強：如果需要，解析網頁正文
                # 策略：如果摘要太短，或者為了獲取更多資訊，可以請求網頁
                # 這裡我們對所有結果嘗試獲取正文，但為了性能，僅獲取前 1000 字元
                content = ""
                if link:
                   try:
                       fetched_content = fetch_url_content(link, timeout=5)
                       if fetched_content:
                           # 如果獲取到了正文，將其拼接到 snippet 中，或者替換 snippet
                           # 這裡選擇拼接，保留原摘要
                           content = fetched_content
                           if len(content) > 500:
                               snippet = f"{snippet}\n\n【網頁詳情】\n{content[:500]}..."
                           else:
                               snippet = f"{snippet}\n\n【網頁詳情】\n{content}"
                   except Exception as e:
                       logger.debug(f"[SerpAPI] Fetch content failed: {e}")

                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=snippet[:1000], # 限制總長度
                    url=link,
                    source=item.get('source', self._extract_domain(link)),
                    published_date=item.get('date'),
                ))

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """從 URL 提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '') or '未知來源'
        except:
            return '未知來源'


class BochaSearchProvider(BaseSearchProvider):
    """
    博查搜尋引擎
    
    特點：
    - 專為 AI 優化的中文搜尋 API
    - 結果準確、摘要完整
    - 支援時間範圍過濾和 AI 摘要
    - 相容 Bing Search API 格式
    
    文件：https://bocha-ai.feishu.cn/wiki/RXEOw02rFiwzGSkd9mUcqoeAnNK
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Bocha")
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """執行博查搜尋"""
        try:
            import requests
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="requests 未安裝，請執行: pip install requests"
            )
        
        try:
            # API 端點
            url = "https://api.bocha.cn/v1/web-search"
            
            # 請求標頭
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 確定時間範圍
            freshness = "oneWeek"
            if days <= 1:
                freshness = "oneDay"
            elif days <= 7:
                freshness = "oneWeek"
            elif days <= 30:
                freshness = "oneMonth"
            else:
                freshness = "oneYear"

            # 請求參數（嚴格按照 API 文件）
            payload = {
                "query": query,
                "freshness": freshness,  # 動態時間範圍
                "summary": True,  # 啟用 AI 摘要
                "count": min(max_results, 50)  # 最大 50 條
            }
            
            # 執行搜尋
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            # 檢查 HTTP 狀態碼
            if response.status_code != 200:
                # 嘗試解析錯誤資訊
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        error_data = response.json()
                        error_message = error_data.get('message', response.text)
                    else:
                        error_message = response.text
                except:
                    error_message = response.text
                
                # 根據錯誤碼處理
                if response.status_code == 403:
                    error_msg = f"餘額不足: {error_message}"
                elif response.status_code == 401:
                    error_msg = f"API KEY 無效: {error_message}"
                elif response.status_code == 400:
                    error_msg = f"請求參數錯誤: {error_message}"
                elif response.status_code == 429:
                    error_msg = f"請求頻率達到限制: {error_message}"
                else:
                    error_msg = f"HTTP {response.status_code}: {error_message}"
                
                logger.warning(f"[Bocha] 搜尋失敗: {error_msg}")
                
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # 解析回應
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"回應 JSON 解析失敗: {str(e)}"
                logger.error(f"[Bocha] {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # 檢查回應代碼
            if data.get('code') != 200:
                error_msg = data.get('msg') or f"API 返回錯誤代碼: {data.get('code')}"
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # 記錄原始回應到日誌
            logger.info(f"[Bocha] 搜尋完成，query='{query}'")
            logger.debug(f"[Bocha] 原始回應: {data}")
            
            # 解析搜尋結果
            results = []
            web_pages = data.get('data', {}).get('webPages', {})
            value_list = web_pages.get('value', [])
            
            for item in value_list[:max_results]:
                # 優先使用 summary（AI 摘要），fallback 到 snippet
                snippet = item.get('summary') or item.get('snippet', '')
                
                # 截取摘要長度
                if snippet:
                    snippet = snippet[:500]
                
                results.append(SearchResult(
                    title=item.get('name', ''),
                    snippet=snippet,
                    url=item.get('url', ''),
                    source=item.get('siteName') or self._extract_domain(item.get('url', '')),
                    published_date=item.get('datePublished'),  # UTC+8 格式，無需轉換
                ))
            
            logger.info(f"[Bocha] 成功解析 {len(results)} 條結果")
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except requests.exceptions.Timeout:
            error_msg = "請求超時"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"網路請求失敗: {str(e)}"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"未知錯誤: {str(e)}"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """從 URL 提取域名作為來源"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or '未知來源'
        except:
            return '未知來源'


class SearchService:
    """
    搜尋服務
    
    功能：
    1. 管理多個搜尋引擎
    2. 自動故障轉移
    3. 結果聚合和格式化
    4. 資料源失敗時的增強搜尋（股價、走勢等）
    """
    
    # 增強搜尋關鍵詞範本
    ENHANCED_SEARCH_KEYWORDS = [
        "{name} 股票 今日 股價",
        "{name} {code} 最新 行情 走勢",
        "{name} 股票 分析 走勢圖",
        "{name} K線 技術分析",
        "{name} {code} 漲跌 成交量",
    ]
    
    def __init__(
        self,
        bocha_keys: Optional[List[str]] = None,
        tavily_keys: Optional[List[str]] = None,
        serpapi_keys: Optional[List[str]] = None,
    ):
        """
        初始化搜尋服務
        
        Args:
            bocha_keys: 博查搜尋 API Key 列表
            tavily_keys: Tavily API Key 列表
            serpapi_keys: SerpAPI Key 列表
        """
        self._providers: List[BaseSearchProvider] = []
        
        # 初始化搜尋引擎（按優先級排序）
        # 1. Bocha 優先（中文搜尋優化，AI 摘要）
        if bocha_keys:
            self._providers.append(BochaSearchProvider(bocha_keys))
            logger.info(f"已配置 Bocha 搜尋，共 {len(bocha_keys)} 個 API Key")
        
        # 2. Tavily（免費額度更多，每月 1000 次）
        if tavily_keys:
            self._providers.append(TavilySearchProvider(tavily_keys))
            logger.info(f"已配置 Tavily 搜尋，共 {len(tavily_keys)} 個 API Key")
        
        # 3. SerpAPI 作為備選（每月 100 次）
        if serpapi_keys:
            self._providers.append(SerpAPISearchProvider(serpapi_keys))
            logger.info(f"已配置 SerpAPI 搜尋，共 {len(serpapi_keys)} 個 API Key")
        
        if not self._providers:
            logger.warning("未配置任何搜尋引擎 API Key，新聞搜尋功能將不可用")
    
    @property
    def is_available(self) -> bool:
        """檢查是否有可用的搜尋引擎"""
        return any(p.is_available for p in self._providers)
    
    def search_stock_news(
        self,
        stock_code: str,
        stock_name: str,
        english_name: Optional[str] = None,
        max_results: int = 5,
        focus_keywords: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        搜尋股票相關新聞
        
        Args:
            stock_code: 股票代碼
            stock_name: 股票名稱
            max_results: 最大返回結果數
            focus_keywords: 重點關注的關鍵詞列表
            
        Returns:
            SearchResponse 物件
        """
        # 智慧確定搜尋時間範圍
        # 策略：
        # 1. 週一至週五：搜尋近 3 天（台股新聞更新較慢，且需覆蓋昨日關鍵資訊）
        # 2. 週六、週日：搜尋近 5 天（覆蓋整週動態）
        today_weekday = datetime.now().weekday()
        if today_weekday >= 5: # 週六(5)、週日(6)
            search_days = 5
        else: # 週一(0) - 週五(4)
            search_days = 3

        # 構建搜尋查詢（優化搜尋效果）
        if focus_keywords:
            # 如果提供了關鍵詞，直接使用關鍵詞作為查詢
            query = " ".join(focus_keywords)
        else:
            # 台股優化：如果是 4 位數字代碼，加上 "台股" 關鍵字，並處理可能的英文名稱
            is_tw_stock = len(stock_code) == 4 and stock_code.isdigit()
            
            # 檢查名稱是否為純英文 (yfinance 抓取的常見情況)
            import re
            is_english_name = bool(re.match(r'^[A-Za-z\s,\.]+$', stock_name))
            
            if is_tw_stock:
                # 構建核心搜尋名稱：中文 + 英文（如果不同且不是純代碼）
                search_name = stock_name
                if english_name and english_name.lower() != stock_name.lower() and english_name != stock_code:
                    # 針對台股，英文名通常太長，取前兩個單字或縮寫
                    clean_eng = english_name.split(',')[0].split(' Corp')[0].split(' Inc')[0]
                    search_name = f"{stock_name} {clean_eng}"
                
                if is_english_name:
                    # 如果只有英文名，優先使用代碼搜尋，並加上台股標籤
                    query = f"台股 {stock_code} 最新消息 新聞"
                else:
                    query = f"台股 {search_name} {stock_code} 最新消息"
            else:
                query = f"{stock_name} {stock_code} 股票 最新消息"

        logger.info(f"搜尋股票新聞: {stock_name}({stock_code}), query='{query}', 時間範圍: 近 {search_days} 天")
        
        # 依次嘗試各個搜尋引擎
        for provider in self._providers:
            if not provider.is_available:
                continue
            
            response = provider.search(query, max_results, days=search_days)
            
            if response.success and response.results:
                logger.info(f"使用 {provider.name} 搜尋成功")
                return response
            else:
                logger.warning(f"{provider.name} 搜尋失敗: {response.error_message}，嘗試下一個引擎")
        
        # 所有引擎都失敗
        return SearchResponse(
            query=query,
            results=[],
            provider="None",
            success=False,
            error_message="所有搜尋引擎都不可用或搜尋失敗"
        )
    
    def search_stock_events(
        self,
        stock_code: str,
        stock_name: str,
        event_types: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        搜尋股票特定事件（年報預告、減持等）
        
        專門針對交易決策相關的重要事件進行搜尋
        
        Args:
            stock_code: 股票代碼
            stock_name: 股票名稱
            event_types: 事件類型列表
            
        Returns:
            SearchResponse 物件
        """
        if event_types is None:
            event_types = ["年報預告", "減持公告", "業績快報"]
        
        # 構建針對性查詢
        event_query = " OR ".join(event_types)
        query = f"{stock_name} ({event_query})"
        
        logger.info(f"搜尋股票事件: {stock_name}({stock_code}) - {event_types}")
        
        # 依次嘗試各個搜尋引擎
        for provider in self._providers:
            if not provider.is_available:
                continue
            
            response = provider.search(query, max_results=5)
            
            if response.success:
                return response
        
        return SearchResponse(
            query=query,
            results=[],
            provider="None",
            success=False,
            error_message="事件搜尋失敗"
        )
    
    def search_comprehensive_intel(
        self,
        stock_code: str,
        stock_name: str,
        english_name: Optional[str] = None,
        max_searches: int = 3
    ) -> Dict[str, SearchResponse]:
        """
        多維度情報搜尋（同時使用多個引擎、多個維度）
        
        搜尋維度：
        1. 最新消息 - 近期新聞動態
        2. 風險排查 - 減持、處罰、利空
        3. 業績預期 - 年報預告、業績快報
        
        Args:
            stock_code: 股票代碼
            stock_name: 股票名稱
            max_searches: 最大搜尋次數
            
        Returns:
            {維度名稱: SearchResponse} 字典
        """
        results = {}
        search_count = 0
        
        is_tw_stock = len(stock_code) == 4 and stock_code.isdigit()
        prefix = "台股 " if is_tw_stock else ""
        
        # 構建核心搜尋名稱：中文 + 英文（如果不同且不是純代碼）
        search_name = stock_name
        if english_name and english_name.lower() != stock_name.lower() and english_name != stock_code:
            # 針對台股，英文名通常太長，取前兩個單字或縮寫
            if is_tw_stock:
                clean_eng = english_name.split(',')[0].split(' Corp')[0].split(' Inc')[0]
                search_name = f"{stock_name} {clean_eng}"
            else:
                search_name = f"{stock_name} {english_name}"
        
        # 定義搜尋維度
        search_dimensions = [
            {
                'name': 'latest_news',
                'query': f"{prefix}{search_name} {stock_code} 最新 新聞 重大 事件",
                'desc': '最新消息'
            },
            {
                'name': 'market_analysis',
                'query': f"{prefix}{search_name} {stock_code} 研報 目標價 評級 深度分析",
                'desc': '機構分析'
            },
            {
                'name': 'risk_check', 
                'query': f"{prefix}{search_name} {stock_code} 減持 處罰 違規 訴訟 利空 風險",
                'desc': '風險排查'
            },
            {
                'name': 'earnings',
                'query': f"{prefix}{search_name} {stock_code} 業績預告 財報 營收 淨利潤 同比增長",
                'desc': '業績預期'
            },
            {
                'name': 'industry',
                'query': f"{prefix}{search_name} {stock_code} 所在行業 競爭對手 市場份額 行業前景",
                'desc': '行業分析'
            },
        ]
        
        logger.info(f"開始多維度情報搜尋: {stock_name}({stock_code})")
        
        # 輪流使用不同的搜尋引擎
        provider_index = 0
        
        for dim in search_dimensions:
            if search_count >= max_searches:
                break
            
            # 選擇搜尋引擎（輪流使用）
            available_providers = [p for p in self._providers if p.is_available]
            if not available_providers:
                break
            
            provider = available_providers[provider_index % len(available_providers)]
            provider_index += 1
            
            logger.info(f"[情報搜尋] {dim['desc']}: 使用 {provider.name}")
            
            response = provider.search(dim['query'], max_results=3)
            results[dim['name']] = response
            search_count += 1
            
            if response.success:
                logger.info(f"[情報搜尋] {dim['desc']}: 獲取 {len(response.results)} 條結果")
            else:
                logger.warning(f"[情報搜尋] {dim['desc']}: 搜尋失敗 - {response.error_message}")
            
            # 短暫延遲避免請求過快
            time.sleep(0.5)
        
        return results
    
    def format_intel_report(self, intel_results: Dict[str, SearchResponse], stock_name: str) -> str:
        """
        格式化情報搜尋結果為報告
        
        Args:
            intel_results: 多維度搜尋結果
            stock_name: 股票名稱
            
        Returns:
            格式化的情報報告文字
        """
        lines = [f"【{stock_name} 情報搜尋結果】"]
        
        # 維度展示順序
        display_order = ['latest_news', 'market_analysis', 'risk_check', 'earnings', 'industry']
        
        for dim_name in display_order:
            if dim_name not in intel_results:
                continue
                
            resp = intel_results[dim_name]
            
            # 獲取維度描述
            dim_desc = dim_name
            if dim_name == 'latest_news': dim_desc = '📰 最新消息'
            elif dim_name == 'market_analysis': dim_desc = '📈 機構分析'
            elif dim_name == 'risk_check': dim_desc = '⚠️ 風險排查'
            elif dim_name == 'earnings': dim_desc = '📊 業績預期'
            elif dim_name == 'industry': dim_desc = '🏭 行業分析'
            
            lines.append(f"\n{dim_desc} (來源: {resp.provider}):")
            if resp.success and resp.results:
                # 增加顯示條數
                for i, r in enumerate(resp.results[:4], 1):
                    date_str = f" [{r.published_date}]" if r.published_date else ""
                    lines.append(f"  {i}. {r.title}{date_str}")
                    # 如果摘要太短，可能資訊量不足
                    snippet = r.snippet[:150] if len(r.snippet) > 20 else r.snippet
                    lines.append(f"     {snippet}...")
            else:
                lines.append("  未找到相關資訊")
        
        return "\n".join(lines)
    
    def batch_search(
        self,
        stocks: List[Dict[str, str]],
        max_results_per_stock: int = 3,
        delay_between: float = 1.0
    ) -> Dict[str, SearchResponse]:
        """
        批量搜尋多隻股票的新聞。
        
        Args:
            stocks: 股票列表
            max_results_per_stock: 每隻股票的最大結果數
            delay_between: 搜尋間隔（秒）
            
        Returns:
            結果字典
        """
        results = {}
        
        for i, stock in enumerate(stocks):
            if i > 0:
                time.sleep(delay_between)
            
            code = stock.get('code', '')
            name = stock.get('name', '')
            
            response = self.search_stock_news(code, name, max_results_per_stock)
            results[code] = response
        
        return results

    def search_stock_price_fallback(
        self,
        stock_code: str,
        stock_name: str,
        max_attempts: int = 3,
        max_results: int = 5
    ) -> SearchResponse:
        """
        資料源失敗時的增強搜尋。
        
        當所有資料源 (efinance, akshare, tushare, baostock, etc.) 無法獲取
        股票資料時，使用搜尋引擎尋找股票趨勢和價格資訊，作為 AI 分析的補充資料。
        
        策略：
        1. 使用多個關鍵詞範本搜尋
        2. 為每個關鍵詞嘗試所有可用的搜尋引擎
        3. 聚合並去重結果
        
        Args:
            stock_code: 股票代碼
            stock_name: 股票名稱
            max_attempts: 最大搜尋嘗試次數（使用不同關鍵詞）
            max_results: 返回的最大結果數
            
        Returns:
            包含聚合結果的 SearchResponse 物件
        """

        if not self.is_available:
            return SearchResponse(
                query=f"{stock_name} 股價走勢",
                results=[],
                provider="None",
                success=False,
                error_message="未配置搜尋引擎 API Key"
            )
        
        logger.info(f"[增強搜尋] 資料源失敗，啟動增強搜尋: {stock_name}({stock_code})")
        
        all_results = []
        seen_urls = set()
        successful_providers = []
        
        # 使用多個關鍵詞範本搜尋
        for i, keyword_template in enumerate(self.ENHANCED_SEARCH_KEYWORDS[:max_attempts]):
            query = keyword_template.format(name=stock_name, code=stock_code)
            
            logger.info(f"[增強搜尋] 第 {i+1}/{max_attempts} 次搜尋: {query}")
            
            # 依次嘗試各個搜尋引擎
            for provider in self._providers:
                if not provider.is_available:
                    continue
                
                try:
                    response = provider.search(query, max_results=3)
                    
                    if response.success and response.results:
                        # 去重並添加結果
                        for result in response.results:
                            if result.url not in seen_urls:
                                seen_urls.add(result.url)
                                all_results.append(result)
                                
                        if provider.name not in successful_providers:
                            successful_providers.append(provider.name)
                        
                        logger.info(f"[增強搜尋] {provider.name} 返回 {len(response.results)} 條結果")
                        break  # 成功後跳到下一個關鍵詞
                    else:
                        logger.debug(f"[增強搜尋] {provider.name} 無結果或失敗")
                        
                except Exception as e:
                    logger.warning(f"[增強搜尋] {provider.name} 搜尋異常: {e}")
                    continue
            
            # 短暫延遲避免請求過快
            if i < max_attempts - 1:
                time.sleep(0.5)
        
        # 彙總結果
        if all_results:
            # 截取前 max_results 條
            final_results = all_results[:max_results]
            provider_str = ", ".join(successful_providers) if successful_providers else "None"
            
            logger.info(f"[增強搜尋] 完成，共獲取 {len(final_results)} 條結果（來源: {provider_str}）")
            
            return SearchResponse(
                query=f"{stock_name}({stock_code}) 股價走勢",
                results=final_results,
                provider=provider_str,
                success=True,
            )
        else:
            logger.warning(f"[增強搜尋] 所有搜尋均未返回結果")
            return SearchResponse(
                query=f"{stock_name}({stock_code}) 股價走勢",
                results=[],
                provider="None",
                success=False,
                error_message="增強搜尋未找到相關資訊"
            )

    def search_stock_with_enhanced_fallback(
        self,
        stock_code: str,
        stock_name: str,
        include_news: bool = True,
        include_price: bool = False,
        max_results: int = 5
    ) -> Dict[str, SearchResponse]:
        """
        綜合搜尋介面（支援新聞和股價資訊）
        
        當 include_price=True 時，會同時搜尋新聞和股價資訊。
        主要用於資料源完全失敗時的兜底方案。
        
        Args:
            stock_code: 股票代碼
            stock_name: 股票名稱
            include_news: 是否搜尋新聞
            include_price: 是否搜尋股價/走勢資訊
            max_results: 每類搜尋的最大結果數
            
        Returns:
            {'news': SearchResponse, 'price': SearchResponse} 字典
        """
        results = {}
        
        if include_news:
            results['news'] = self.search_stock_news(
                stock_code, 
                stock_name, 
                max_results=max_results
            )
        
        if include_price:
            results['price'] = self.search_stock_price_fallback(
                stock_code,
                stock_name,
                max_attempts=3,
                max_results=max_results
            )
        
        return results

    def format_price_search_context(self, response: SearchResponse) -> str:
        """
        將股價搜尋結果格式化為 AI 分析上下文
        
        Args:
            response: 搜尋回應物件
            
        Returns:
            格式化的文字，可直接用於 AI 分析
        """
        if not response.success or not response.results:
            return "【股價走勢搜尋】未找到相關資訊，請以其他管道資料為準。"
        
        lines = [
            f"【股價走勢搜尋結果】（來源: {response.provider}）",
            "⚠️ 注意：以下資訊來自網路搜尋，僅供參考，可能存在延遲或不準確。",
            ""
        ]
        
        for i, result in enumerate(response.results, 1):
            date_str = f" [{result.published_date}]" if result.published_date else ""
            lines.append(f"{i}. 【{result.source}】{result.title}{date_str}")
            lines.append(f"   {result.snippet[:200]}...")
            lines.append("")
        
        return "\n".join(lines)


# === 便捷函數 ===
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """獲取搜尋服務單體"""
    global _search_service
    
    if _search_service is None:
        from tradingagents.daily_analysis.config import get_config
        config = get_config()
        
        _search_service = SearchService(
            bocha_keys=config.bocha_api_keys,
            tavily_api_keys=config.tavily_api_keys,
            serpapi_keys=config.serpapi_keys,
        )
    
    return _search_service


def reset_search_service() -> None:
    """重置搜尋服務（用於測試）"""
    global _search_service
    _search_service = None


if __name__ == "__main__":
    # 測試搜尋服務
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    )
    
    # 手動測試（需要配置 API Key）
    service = get_search_service()
    
    if service.is_available:
        print("=== 測試股票新聞搜尋 ===")
        response = service.search_stock_news("300389", "艾比森")
        print(f"搜尋狀態: {'成功' if response.success else '失敗'}")
        print(f"搜尋引擎: {response.provider}")
        print(f"結果數量: {len(response.results)}")
        print(f"耗時: {response.search_time:.2f}s")
        print("\n" + response.to_context())
    else:
        print("未配置搜尋引擎 API Key，跳過測試")
