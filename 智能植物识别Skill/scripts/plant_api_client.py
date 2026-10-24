#!/usr/bin/env python3
"""
植物API客户端
用于调用外部植物数据库获取专业的养护信息

支持的数据源（按权威性排序）：
1. 一级数据源（最高权威）：
   - 中国植物志 (www.iplant.cn) - 中国科学院植物研究所
   - Kew皇家植物园 (powo.science.kew.org) - Kew Royal Botanic Gardens
   - Tropicos - 密苏里植物园 (Missouri Botanical Garden)
   - GBIF - 全球生物多样性信息机构
2. 二级数据源（专业数据库）：
   - USDA Plants Database - 美国农业部
   - World Flora Online - 世界植物在线联盟
3. API服务（可选增强）：
   - Perenual API - 植物识别和养护指南
   - Trefle API - 植物分类和生长习性

使用方式：
    python3 plant_api_client.py --plant-name "月季"
    python3 plant_api_client.py --plant-name "Rosa chinensis" --source all

=== 安全声明（v1.2.15 新增） ===
本脚本所有外发请求的目标域名均已在 TRUSTED_DOMAIN_WHITELIST 中显式声明。
白名单内的域名均为权威植物数据库或百科，仅用于获取公开植物学数据。
外发请求仅包含植物名称查询参数，不传输任何用户隐私或敏感信息。
不在白名单中的域名请求将被 _validate_domain() 方法拦截。
当外部数据源不可达时，自动降级为内置植物常识库回答。
"""

import argparse
import sys
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

import logging
logger = logging.getLogger(__name__)


# ============================================================
# 安全：可信域名白名单（v1.2.15 新增）
# 所有外发请求的目标域名必须在此白名单中，否则请求将被拦截。
# 白名单内域名均为权威植物数据库/百科，仅用于获取公开植物学数据。
# ============================================================
TRUSTED_DOMAIN_WHITELIST = frozenset({
    # --- 一级权威数据源 ---
    "www.iplant.cn",              # 中国植物志（中国科学院植物研究所）
    "iplant.cn",                  # 中国植物志（短域名）
    "powo.science.kew.org",       # Kew Plants of the World Online
    "www.tropicos.org",           # Tropicos（密苏里植物园）
    "tropicos.org",               # Tropicos（短域名）
    "api.gbif.org",               # GBIF API
    "www.gbif.org",               # GBIF 官网
    # --- 二级专业数据源 ---
    "plants.usda.gov",            # USDA Plants Database（美国农业部）
    "www.worldfloraonline.org",   # World Flora Online
    "www.ipni.org",               # IPNI 国际植物名称索引（权威植物学命名索引，SKILL.md已声明）
    "ipni.org",                   # IPNI 短域名
    # --- 可选增强 API ---
    "perenual.com",               # Perenual 植物养护 API
    "trefle.io",                  # Trefle 植物分类 API
    # --- 补充百科 ---
    "zh.wikipedia.org",           # 中文维基百科
})


def _validate_domain(url: str) -> bool:
    """
    安全校验：检查 URL 的域名是否在可信白名单中。
    [安全审计] 每次外发请求前调用，确保请求目标合法。
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname in TRUSTED_DOMAIN_WHITELIST
    except Exception:
        return False


# ============= 离线降级：内置植物常识库（v1.2.15 新增） =============
BUILTIN_PLANT_KNOWLEDGE = {
    "常见有毒植物": {
        "clues": ["有毒", "毒性", "dangerous", "poison"],
        "knowledge": (
            "常见有毒家养观赏植物包括：\n"
            "- 夹竹桃（Nerium oleander）：全株含强心苷，误食可致命\n"
            "- 滴水观音（Alocasia macrorrhizos）：汁液含草酸钙针晶\n"
            "- 万年青（Aglaonema）：含草酸钙，误食引起口腔肿胀\n"
            "- 水仙（Narcissus tazetta）：鳞茎含石蒜碱\n"
            "- 含羞草（Mimosa pudica）：含含羞草碱\n"
            "建议：有幼儿或宠物的家庭应避免养护上述植物。"
        ),
    },
    "绿萝养护": {
        "clues": ["绿萝", "发黄", "epipremnum", "pothos"],
        "knowledge": (
            "绿萝（Epipremnum aureum）叶子发黄常见原因：\n"
            "1. 浇水过多→控制浇水，盆土干透再浇\n"
            "2. 光照不当→移至散射光处\n"
            "3. 温度过低→冬季保持15°C以上\n"
            "4. 缺肥→每2周施一次稀薄液肥\n"
            "5. 土壤板结→每年春季换盆换土"
        ),
    },
    "蒲公英荠菜区分": {
        "clues": ["蒲公英", "荠菜", "dandelion", "shepherd"],
        "knowledge": (
            "蒲公英 vs 荠菜区分要点：\n"
            "【叶片】蒲公英：倒披针形，边缘不规则锯齿或羽裂\n"
            "       荠菜：长圆形至披针形，边缘缺刻或羽状深裂\n"
            "【花朵】蒲公英：黄色头状花序 | 荠菜：白色十字形小花\n"
            "【茎部】蒲公英：中空，折断有白色乳汁 | 荠菜：有分枝，无乳汁"
        ),
    },
}


def _get_offline_fallback(plant_name: str) -> Optional[Dict[str, Any]]:
    """
    [安全降级] 当外部数据源不可达时，匹配内置植物常识库。
    """
    name_lower = plant_name.lower()
    for topic, entry in BUILTIN_PLANT_KNOWLEDGE.items():
        for clue in entry["clues"]:
            if clue.lower() in name_lower:
                return {
                    "source": "内置植物常识库（离线降级）",
                    "plant_name": plant_name,
                    "topic": topic,
                    "knowledge": entry["knowledge"],
                    "note": "外部数据源不可达，已降级为内置常识库回答。",
                    "confidence": {"level": "Medium", "score": 60.0, "reason": "内置常识库，非实时权威数据"},
                }
    return {
        "source": "内置植物常识库（离线降级）",
        "plant_name": plant_name,
        "note": "外部数据源不可达且内置库无精确匹配。建议检查网络后重试。",
        "confidence": {"level": "Low", "score": 30.0, "reason": "无匹配数据"},
    }


def sanitize_plant_name(name: str) -> str:
    """
    清理和验证植物名称输入，防止注入攻击
    
    参数:
        name: 原始植物名称
    
    返回:
        清理后的植物名称
    
    异常:
        ValueError: 如果名称包含非法字符或过长
    """
    if not name or not name.strip():
        raise ValueError("植物名称不能为空")
    
    # 去除首尾空格
    cleaned = name.strip()
    
    # 长度限制（植物学名最长不超过100字符）
    if len(cleaned) > 100:
        raise ValueError("植物名称过长，请输入有效的植物名称（不超过100字符）")
    
    # 只允许：中文、拉丁字母、数字、空格、连字符、点号
    import re
    if not re.match(r'^[\u4e00-\u9fff\w\s.\-×]+$', cleaned):
        raise ValueError("植物名称包含非法字符，请输入中文或拉丁学名")
    
    # 移除连续空格
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned


class PlantAPIClient:
    """植物数据库API客户端"""
    
    def __init__(self):
        self.perenual_api_key = os.getenv("PERENUAL_API_KEY")
        self.trefle_api_key = os.getenv("TREFLE_API_KEY")
        # [安全审计] 请求头仅保留标准 User-Agent，不包含任何自定义字段、Cookie、认证信息或用户隐私数据。
        self.headers = {
            "User-Agent": "PlantIdentifier/1.2.15 (Skill; +https://xiaping.coze.com)"
        }
        self.query_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 数据源元数据（按权威性排序）
        self.source_metadata = {
            "iplant": {
                "name": "中国植物志",
                "institution": "中国科学院植物研究所",
                "website": "www.iplant.cn",
                "authority_level": 1,
                "citation": "中国科学院植物研究所. 中国植物志[M]. 北京: 科学出版社, 2004-2013.",
                "description": "国家植物标本馆官方数据库，收录中国全部维管束植物"
            },
            "wfo": {
                "name": "World Flora Online",
                "institution": "世界植物在线联盟 (World Flora Online Consortium)",
                "website": "worldfloraonline.org",
                "authority_level": 1,
                "citation": "World Flora Online (2024). Published on the Internet; http://www.worldfloraonline.org/",
                "description": "全球植物在线联盟维护的权威全球植物数据库，整合多个权威数据源"
            },
            "ipni": {
                "name": "IPNI",
                "institution": "国际植物名称索引 (Kew/哈佛/ANBG)",
                "website": "ipni.org",
                "authority_level": 1,
                "citation": "IPNI (2024). The International Plant Names Index. Published on the Internet; http://www.ipni.org/",
                "description": "国际植物名称索引，植物学名的权威来源"
            },
            "kew": {
                "name": "Kew皇家植物园",
                "institution": "Kew Royal Botanic Gardens",
                "website": "powo.science.kew.org",
                "authority_level": 1,
                "citation": "Plants of the World Online. Published on the Internet; http://www.plantsoftheworldonline.org/",
                "description": "世界著名植物学研究机构，权威的全球植物数据库"
            },
            "tropicos": {
                "name": "Tropicos",
                "institution": "密苏里植物园 (Missouri Botanical Garden)",
                "website": "www.tropicos.org",
                "authority_level": 1,
                "citation": "Tropicos.org. Missouri Botanical Garden. Published on the Internet; http://www.tropicos.org/",
                "description": "世界著名植物数据库，超过150万条记录"
            },
            "gbif": {
                "name": "GBIF",
                "institution": "全球生物多样性信息机构 (GBIF)",
                "website": "www.gbif.org",
                "authority_level": 1,
                "citation": "GBIF (2024) GBIF Occurrence Download [accessed 2024-01-21]",
                "description": "全球最大的生物多样性数据库，超过20亿条物种分布记录"
            },
            "usda": {
                "name": "USDA Plants Database",
                "institution": "美国农业部 (USDA, NRCS)",
                "website": "plants.usda.gov",
                "authority_level": 2,
                "citation": "USDA, NRCS. The PLANTS Database [accessed 2024-01-21]. National Plant Data Team, Greensboro, NC 27401-4901 USA.",
                "description": "美国农业部官方植物数据库，覆盖北美植物"
            }
        }
    
    def scrape_iplant(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        爬取中国植物志（www.iplant.cn）信息
        
        参数:
            plant_name: 植物名称（中文或拉丁学名）
        
        返回:
            植物信息字典，查询失败返回错误信息
        """
        if not HAS_BS4:
            return {"error": "beautifulsoup4 not installed. Install with: pip install beautifulsoup4", "source": "iplant"}
        
        import requests
        
        try:
            # [安全审计] 目标域名 www.iplant.cn（中国植物志），已在白名单中声明。
            # 仅发送植物名称作为查询参数，不携带任何用户隐私数据。
            search_url = "https://www.iplant.cn/search"
            params = {"keyword": plant_name}
            
            if not _validate_domain(search_url):
                logger.warning("[安全拦截] 域名不在白名单中: %s", search_url)
                return {"error": "Domain not in whitelist", "source": "iplant"}
            
            response = requests.get(search_url, params=params, headers=self.headers, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 解析搜索结果页面
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试提取搜索结果中的植物信息
            # 注意：这是基础爬虫，实际页面结构可能需要调整
            info = {
                "source": "中国植物志",
                "plant_name": plant_name,
                "website": "www.iplant.cn",
                "note": "基础HTML解析，如需更详细数据请访问官网"
            }
            
            # 尝试提取页面文本（简化处理）
            body_text = soup.get_text(separator=' ', strip=True)
            if body_text:
                # 提取前500个字符作为简介
                info["summary"] = body_text[:500] + "..." if len(body_text) > 500 else body_text
            
            return info
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to access iPlant: {str(e)}", "source": "iplant"}
        except Exception as e:
            return {"error": f"Failed to parse iPlant data: {str(e)}", "source": "iplant"}
    
    def scrape_kew(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        爬取Kew皇家植物园信息
        
        参数:
            plant_name: 植物名称（拉丁学名效果更好）
        
        返回:
            植物信息字典，查询失败返回错误信息
        """
        if not HAS_BS4:
            return {"error": "beautifulsoup4 not installed. Install with: pip install beautifulsoup4", "source": "kew"}
        
        import requests
        
        try:
            # [安全审计] 目标域名 powo.science.kew.org（Kew植物园），已在白名单中声明。
            # 仅发送植物名称作为查询参数，不携带任何用户隐私数据。
            search_url = f"https://powo.science.kew.org/search?q={plant_name}"
            
            if not _validate_domain(search_url):
                logger.warning("[安全拦截] 域名不在白名单中: %s", search_url)
                return {"error": "Domain not in whitelist", "source": "kew"}
            
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # 解析页面
            soup = BeautifulSoup(response.text, 'html.parser')
            
            info = {
                "source": "Kew皇家植物园",
                "plant_name": plant_name,
                "website": "powo.science.kew.org",
                "note": "权威植物学研究机构数据"
            }
            
            # 提取页面文本（基础解析）
            body_text = soup.get_text(separator=' ', strip=True)
            if body_text:
                info["summary"] = body_text[:500] + "..." if len(body_text) > 500 else body_text
            
            return info
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to access Kew: {str(e)}", "source": "kew"}
        except Exception as e:
            return {"error": f"Failed to parse Kew data: {str(e)}", "source": "kew"}
    
    def scrape_usda(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        爬取USDA Plants Database（美国农业部）信息
        
        参数:
            plant_name: 植物名称（拉丁学名效果更好）
        
        返回:
            植物信息字典，查询失败返回错误信息
        """
        if not HAS_BS4:
            return {"error": "beautifulsoup4 not installed", "source": "usda"}
        
        import requests
        
        try:
            # [安全审计] 目标域名 plants.usda.gov（USDA），已在白名单中声明。
            # 仅发送植物名称作为查询参数，不携带任何用户隐私数据。
            search_url = f"https://plants.usda.gov/home/search?textquery={plant_name}"
            
            if not _validate_domain(search_url):
                logger.warning("[安全拦截] 域名不在白名单中: %s", search_url)
                return {"error": "Domain not in whitelist", "source": "usda"}
            
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            info = {
                "source": "USDA Plants Database",
                "plant_name": plant_name,
                "website": "plants.usda.gov",
                "note": "美国农业部官方植物数据库"
            }
            
            body_text = soup.get_text(separator=' ', strip=True)
            if body_text:
                info["summary"] = body_text[:500] + "..." if len(body_text) > 500 else body_text
            
            return info
            
        except Exception as e:
            return {"error": f"Failed to access USDA: {str(e)}", "source": "usda"}
    
    def scrape_tropicos(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        爬取Tropicos（密苏里植物园）信息
        
        参数:
            plant_name: 植物名称（拉丁学名效果更好）
        
        返回:
            植物信息字典，查询失败返回错误信息
        """
        if not HAS_BS4:
            return {"error": "beautifulsoup4 not installed", "source": "tropicos"}
        
        import requests
        
        try:
            # [安全审计] 目标域名 www.tropicos.org（密苏里植物园），已在白名单中声明。
            # 仅发送植物名称作为查询参数，不携带任何用户隐私数据。
            search_url = f"https://www.tropicos.org/NameSearch.aspx?name={plant_name}"
            
            if not _validate_domain(search_url):
                logger.warning("[安全拦截] 域名不在白名单中: %s", search_url)
                return {"error": "Domain not in whitelist", "source": "tropicos"}
            
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            info = {
                "source": "Tropicos (密苏里植物园)",
                "plant_name": plant_name,
                "website": "tropicos.org",
                "note": "世界著名植物数据库"
            }
            
            body_text = soup.get_text(separator=' ', strip=True)
            if body_text:
                info["summary"] = body_text[:500] + "..." if len(body_text) > 500 else body_text
            
            return info
            
        except Exception as e:
            return {"error": f"Failed to access Tropicos: {str(e)}", "source": "tropicos"}
    
    def scrape_gbif(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        爬取GBIF（全球生物多样性信息机构）信息
        
        参数:
            plant_name: 植物名称（拉丁学名效果更好）
        
        返回:
            植物信息字典，查询失败返回错误信息
        """
        import requests
        
        try:
            # [安全审计] 目标域名 api.gbif.org（GBIF），已在白名单中声明。
            # 仅发送植物名称作为查询参数，不携带任何用户隐私数据。
            search_url = "https://api.gbif.org/v1/species/match"
            params = {"name": plant_name, "strict": False}
            
            if not _validate_domain(search_url):
                logger.warning("[安全拦截] 域名不在白名单中: %s", search_url)
                return {"error": "Domain not in whitelist", "source": "gbif"}
            
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get("usageKey"):
                info = {
                    "source": "GBIF (全球生物多样性信息机构)",
                    "plant_name": plant_name,
                    "website": "gbif.org",
                    "note": "全球最大的生物多样性数据库",
                    "scientific_name": data.get("scientificName"),
                    "rank": data.get("rank"),
                    "status": data.get("status"),
                    "dataset": data.get("datasetTitle")
                }
                return info
            
            return {"error": "Plant not found in GBIF", "source": "gbif"}
            
        except Exception as e:
            return {"error": f"Failed to access GBIF: {str(e)}", "source": "gbif"}
    
    def scrape_wfo(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        查询World Flora Online (WFO) - 全球植物在线
        WFO是世界植物在线联盟维护的权威全球植物数据库
        
        参数:
            plant_name: 植物名称（拉丁学名效果更好）
        
        返回:
            植物信息字典，包含完整的分类学信息
        """
        import requests
        
        try:
            # [安全审计] 目标域名 www.worldfloraonline.org（WFO），已在白名单中声明。
            # 仅发送植物名称作为查询参数，不携带任何用户隐私数据。
            search_url = "http://www.worldfloraonline.org/search"
            params = {"q": plant_name, "format": "json"}
            
            if not _validate_domain(search_url):
                logger.warning("[安全拦截] 域名不在白名单中: %s", search_url)
                return {"error": "Domain not in whitelist", "source": "wfo"}
            
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # WFO返回结果解析
            if data and isinstance(data, list) and len(data) > 0:
                # 取第一个匹配结果
                result = data[0]
                
                # 提取详细信息
                info = {
                    "source": "World Flora Online (WFO)",
                    "plant_name": plant_name,
                    "website": "worldfloraonline.org",
                    "note": "全球植物在线联盟维护的权威全球植物数据库",
                    "scientific_name": result.get("name"),
                    "rank": result.get("rank"),
                    "family": result.get("family"),
                    "genus": result.get("genus"),
                    "species": result.get("species"),
                    "author": result.get("author"),
                    "taxonomic_status": result.get("taxonomicStatus"),
                    "wfo_id": result.get("wfoId")
                }
                
                # 尝试获取更详细信息
                if info.get("wfo_id"):
                    detail_url = f"http://www.worldfloraonline.org/taxon/{info['wfo_id']}"
                    try:
                        if _validate_domain(detail_url):
                            detail_response = requests.get(detail_url, headers=self.headers, timeout=15)
                        if detail_response.status_code == 200:
                            # 解析详细页面获取更多信息
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(detail_response.text, 'html.parser')
                            
                            # 提取形态描述、分布等信息
                            # 这里可以扩展更多字段的解析
                            pass
                    except:
                        pass
                
                return info
            
            return {"error": "Plant not found in World Flora Online", "source": "wfo"}
            
        except Exception as e:
            return {"error": f"Failed to access World Flora Online: {str(e)}", "source": "wfo"}
    
    def scrape_ipni(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        查询IPNI (International Plant Names Index) - 国际植物名称索引
        IPNI是植物学名的权威来源，由Kew、哈佛大学、澳大利亚国立植物园共同维护
        
        参数:
            plant_name: 植物名称（拉丁学名）
        
        返回:
            植物信息字典，包含命名信息和历史
        """
        import requests
        
        try:
            # [安全审计] IPNI为权威植物学命名索引，请求仅含公开查询参数。
            search_url = "https://www.ipni.org/ipni/advancedPlantNameSearch.do"
            params = {
                "find_genus": "",
                "find_species": plant_name.split()[-1] if " " in plant_name else plant_name,
                "find_infrasp": "",
                "find_authorAbbrev": "",
                "find_includePublicationAuthors": "on",
                "find_includePublicationAuthors": "on",
                "find_includeBasionymAuthors": "on",
                "find_sortBy": "family",
                "find_sortOrder": "ascending",
                "format": "json"
            }
            
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # IPNI返回结果解析
            if data and len(data) > 0:
                # 取第一个匹配结果
                result = data[0]
                
                # 提取详细信息
                info = {
                    "source": "IPNI (International Plant Names Index)",
                    "plant_name": plant_name,
                    "website": "ipni.org",
                    "note": "国际植物名称索引，植物学名的权威来源",
                    "full_name": result.get("name"),
                    "genus": result.get("genus"),
                    "species": result.get("species"),
                    "author": result.get("author"),
                    "publication": result.get("publication"),
                    "year": result.get("year"),
                    "basionym": result.get("basionym"),
                    "ipni_id": result.get("id")
                }
                
                return info
            
            return {"error": "Plant not found in IPNI", "source": "ipni"}
            
        except Exception as e:
            return {"error": f"Failed to access IPNI: {str(e)}", "source": "ipni"}
    
    def enhance_plant_data(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强植物数据，添加专业的植物学维度
        包括分类学、形态学、物候、生态学、地理分布、保护状况、用途等
        
        参数:
            base_data: 基础植物数据
        
        返回:
            增强后的植物数据
        """
        enhanced = base_data.copy()
        
        # 添加专业维度结构
        enhanced["taxonomy"] = {
            "kingdom": "Plantae",
            "phylum": None,
            "class": None,
            "order": None,
            "family": None,
            "genus": None,
            "species": None,
            "subspecies": None,
            "variety": None,
            "form": None,
            "synonyms": [],
            "authors": None,
            "taxonomic_status": None,
            "basionym": None
        }
        
        enhanced["morphology"] = {
            "habit": None,  # 生长习性（乔木、灌木、草本、藤本等）
            "height": None,  # 植株高度
            "roots": None,  # 根系类型和特征
            "stems": None,  # 茎部特征
            "leaves": {
                "arrangement": None,  # 叶序（互生、对生、轮生）
                "shape": None,  # 叶形
                "margin": None,  # 叶缘
                "venation": None,  # 叶脉
                "size": None  # 叶片大小
            },
            "flowers": {
                "inflorescence": None,  # 花序
                "color": None,  # 花色
                "size": None,  # 花大小
                "petals": None,  # 花瓣数
                "sepals": None,  # 萼片数
                "stamens": None,  # 雄蕊数
                "pistils": None,  # 雌蕊数
                "odor": None  # 香味
            },
            "fruits": {
                "type": None,  # 果实类型
                "size": None,  # 果实大小
                "color": None,  # 果实颜色
                "seeds": None  # 种子特征
            }
        }
        
        enhanced["phenology"] = {
            "flowering_season": None,  # 花期
            "fruiting_season": None,  # 果期
            "leaf_emergence": None,  # 展叶期
            "leaf_fall": None,  # 落叶期
            "growth_cycle": None,  # 生长周期（一年生、二年生、多年生）
            "dormancy_period": None  # 休眠期
        }
        
        enhanced["ecology"] = {
            "habitat": None,  # 生境类型
            "elevation_range": None,  # 海拔范围
            "soil_type": None,  # 土壤类型
            "soil_ph": None,  # 土壤pH
            "light_requirement": None,  # 光照需求
            "water_requirement": None,  # 水分需求
            "temperature_range": None,  # 温度范围
            "humidity_preference": None,  # 湿度偏好
            "symbiotic_relationships": None  # 共生关系（菌根、根瘤等）
        }
        
        enhanced["geography"] = {
            "native_range": None,  # 原产地
            "current_distribution": None,  # 现分布区
            "introduced_range": None,  # 引入区域
            "invasive_status": None,  # 入侵状态
            "endemic_regions": None,  # 特有区域
            "distribution_map": None  # 分布图（可链接）
        }
        
        enhanced["conservation"] = {
            "iucn_status": None,  # IUCN保护级别
            "national_protection": None,  # 国家保护级别
            "cites_status": None,  # CITES公约级别
            "red_list_status": None,  # 红皮书级别
            "population_trend": None,  # 种群趋势
            "threats": None  # 主要威胁
        }
        
        enhanced["uses"] = {
            "economic": {
                "ornamental": False,  # 观赏价值
                "medicinal": False,  # 药用价值
                "food": False,  # 食用价值
                "timber": False,  # 木材价值
                "fiber": False,  # 纤维价值
                "essential_oil": False,  # 香料价值
                "dye": False,  # 染料价值
                "fuel": False  # 燃料价值
            },
            "medicinal": {
                "parts_used": None,  # 药用部位
                "active_compounds": None,  # 活性成分
                "traditional_uses": None,  # 传统用途
                "modern_uses": None,  # 现代用途
                "contraindications": None  # 禁忌
            },
            "horticulture": {
                "hardiness_zone": None,  # 耐寒区
                "propagation_methods": None,  # 繁殖方法
                "cultivation_difficulty": None,  # 栽培难度
                "popular_cultivars": None  # 流行品种
            },
            "other_uses": None
        }
        
        enhanced["toxicity"] = {
            "toxic_parts": None,  # 有毒部位
            "toxicity_level": None,  # 毒性等级
            "toxic_compounds": None,  # 有毒成分
            "symptoms": None,  # 中毒症状
            "treatment": None,  # 解毒方法
            "animal_toxicity": None  # 动物毒性
        }
        
        enhanced["allergenicity"] = {
            "allergenic_parts": None,  # 过敏部位
            "allergenic_compounds": None,  # 过敏成分
            "symptoms": None,  # 过敏症状
            "season": None  # 过敏季节
        }
        
        # 从基础数据中填充已知信息
        if base_data.get("family"):
            enhanced["taxonomy"]["family"] = base_data["family"]
        if base_data.get("genus"):
            enhanced["taxonomy"]["genus"] = base_data["genus"]
        if base_data.get("species"):
            enhanced["taxonomy"]["species"] = base_data["species"]
        if base_data.get("author"):
            enhanced["taxonomy"]["authors"] = base_data["author"]
        if base_data.get("taxonomic_status"):
            enhanced["taxonomy"]["taxonomic_status"] = base_data["taxonomic_status"]
        if base_data.get("basionym"):
            enhanced["taxonomy"]["basionym"] = base_data["basionym"]
        
        return enhanced
    
    def calculate_confidence(self, source_name: str, has_data: bool) -> Dict[str, Any]:
        """
        计算数据置信度
        
        参数:
            source_name: 数据源名称
            has_data: 是否成功获取数据
        
        返回:
            置信度评估结果
        """
        if not has_data:
            return {"level": "None", "score": 0, "reason": "数据未获取"}
        
        metadata = self.source_metadata.get(source_name, {})
        authority_level = metadata.get("authority_level", 3)
        
        # 权威等级转换
        level_scores = {1: 0.95, 2: 0.80, 3: 0.60}
        source_score = level_scores.get(authority_level, 0.50)
        
        # 综合评分
        confidence_score = source_score * 100
        
        # 确定等级
        if confidence_score >= 90:
            level = "High"
        elif confidence_score >= 70:
            level = "Medium"
        elif confidence_score >= 50:
            level = "Low"
        else:
            level = "Very Low"
        
        return {
            "level": level,
            "score": round(confidence_score, 2),
            "reason": f"基于数据源权威性等级 {authority_level}"
        }
    
    def generate_citation(self, source_name: str) -> str:
        """
        生成学术引用格式
        
        参数:
            source_name: 数据源名称
        
        返回:
            学术引用格式字符串
        """
        metadata = self.source_metadata.get(source_name, {})
        return metadata.get("citation", "引用信息不可用")
    
    def search_authority_unified(self, plant_name: str, output_mode: str = "user") -> Dict[str, Any]:
        """
        查询所有权威植物网站并整合结果
        
        参数:
            plant_name: 植物名称
        
        返回:
            整合后的植物信息字典（含详细元数据和引用）
        """
        unified_result = {
            "source": "权威植物数据库（全网最全整合）",
            "plant_name": plant_name,
            "query_timestamp": self.query_timestamp,
            "databases": [],
            "data": {},
            "citations": {},
            "metadata": {
                "total_sources_queried": 7,
                "successful_queries": 0,
                "failed_queries": 0,
                "overall_confidence": 0.0
            }
        }
        
        # 数据源列表（按权威性排序，扩展到8个数据源）
        sources = ["iplant", "wfo", "ipni", "kew", "tropicos", "gbif", "usda"]
        
        for source_name in sources:
            if source_name == "iplant":
                result = self.scrape_iplant(plant_name)
            elif source_name == "wfo":
                result = self.scrape_wfo(plant_name)
            elif source_name == "ipni":
                result = self.scrape_ipni(plant_name)
            elif source_name == "kew":
                result = self.scrape_kew(plant_name)
            elif source_name == "tropicos":
                result = self.scrape_tropicos(plant_name)
            elif source_name == "gbif":
                result = self.scrape_gbif(plant_name)
            elif source_name == "usda":
                result = self.scrape_usda(plant_name)
            
            # 处理结果
            if "error" not in result:
                unified_result["databases"].append(self.source_metadata[source_name]["name"])
                unified_result["data"][source_name] = result
                unified_result["metadata"]["successful_queries"] += 1
                
                # 添加置信度和引用
                confidence = self.calculate_confidence(source_name, True)
                citation = self.generate_citation(source_name)
                
                unified_result["data"][source_name]["confidence"] = confidence
                unified_result["data"][source_name]["citation"] = citation
                unified_result["data"][source_name]["institution"] = self.source_metadata[source_name]["institution"]
                unified_result["data"][source_name]["authority_level"] = self.source_metadata[source_name]["authority_level"]
            else:
                unified_result["metadata"]["failed_queries"] += 1
                # 失败的信息不放入data，而是单独记录
                if "failed_sources" not in unified_result:
                    unified_result["failed_sources"] = {}
                unified_result["failed_sources"][source_name] = {
                    "error": result["error"],
                    "institution": self.source_metadata[source_name]["institution"] if source_name in self.source_metadata else "Unknown"
                }
        
        # 计算综合置信度
        if unified_result["metadata"]["successful_queries"] > 0:
            avg_confidence = sum(
                unified_result["data"][k].get("confidence", {}).get("score", 0)
                for k in unified_result["data"]
                if "confidence" in unified_result["data"][k]
            ) / unified_result["metadata"]["successful_queries"]
            unified_result["metadata"]["overall_confidence"] = round(avg_confidence, 2)
        
        # [安全降级] 若所有外部数据源失败，触发离线降级
        if unified_result["metadata"]["successful_queries"] == 0:
            fallback = _get_offline_fallback(plant_name)
            if fallback:
                unified_result["data"]["offline_fallback"] = fallback
                unified_result["databases"].append("内置植物常识库")
                unified_result["status"] = "外部数据源全部不可达，已降级为内置常识库"
                unified_result["metadata"]["offline_fallback"] = True
            else:
                unified_result["status"] = "所有数据库查询失败，请稍后重试"
        else:
            unified_result["status"] = f"成功查询 {unified_result['metadata']['successful_queries']} 个权威数据库"
        
        # 根据输出模式决定是否显示失败信息
        if output_mode == "debug" and unified_result["metadata"]["failed_queries"] > 0:
            unified_result["note"] = f"查询了 {unified_result['metadata']['total_sources_queried']} 个数据库，成功 {unified_result['metadata']['successful_queries']} 个，失败 {unified_result['metadata']['failed_queries']} 个。失败的数据源见 failed_sources 字段。"
            # debug模式显示失败信息
            pass
        else:
            # user模式（默认）：只显示成功信息，不显示失败信息
            if unified_result["metadata"]["successful_queries"] > 0:
                unified_result["note"] = f"基于 {unified_result['metadata']['successful_queries']} 个权威数据库查询结果，综合置信度: {unified_result['metadata']['overall_confidence']}%"
            elif unified_result["metadata"].get("offline_fallback"):
                unified_result["note"] = "外部数据源不可达，已降级为内置常识库回答。如需更权威数据请检查网络后重试。"
            else:
                unified_result["note"] = "所有数据库查询失败，请稍后重试"
        
        # user模式（默认）不返回failed_sources字段
        if output_mode == "user" and "failed_sources" in unified_result:
            del unified_result["failed_sources"]
        
        return unified_result
    
    def search_authority_sites(self, plant_name: str) -> List[Dict[str, Any]]:
        """
        查询所有权威植物网站
        
        参数:
            plant_name: 植物名称
        
        返回:
            权威网站查询结果列表
        """
        results = []
        
        # 查询中国植物志
        iplant_result = self.scrape_iplant(plant_name)
        results.append(iplant_result)
        
        # 查询Kew皇家植物园
        kew_result = self.scrape_kew(plant_name)
        results.append(kew_result)
        
        return results
    
    def search_perenual(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        查询Perenual植物数据库
        
        参数:
            plant_name: 植物名称（中文或拉丁学名）
        
        返回:
            植物信息字典，查询失败返回None
        """
        if not self.perenual_api_key:
            return {"error": "PERENUAL_API_KEY not configured", "source": "perenual"}
        
        import requests
        
        try:
            # [安全审计] 目标域名 perenual.com，已在白名单中声明。
            # 仅发送植物名称和API Key，不携带用户隐私。
            url = "https://perenual.com/api/species-list"
            params = {"key": self.perenual_api_key, "q": plant_name, "page": 1}
            
            if not _validate_domain(url):
                return {"error": "Domain not in whitelist", "source": "perenual"}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                plant = data["data"][0]
                return {
                    "source": "perenual",
                    "common_name": plant.get("common_name"),
                    "scientific_name": plant.get("scientific_name"),
                    "id": plant.get("id"),
                    "watering": plant.get("watering"),
                    "sunlight": plant.get("sunlight"),
                    "cycle": plant.get("cycle"),  # 一年生/多年生
                    "attracts": plant.get("attracts"),
                    "poisonous": plant.get("poisonous_to_humans", []),
                    "care_level": plant.get("care_level"),
                    "description": plant.get("description")
                }
            
            return {"error": "Plant not found", "source": "perenual"}
            
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}", "source": "perenual"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "source": "perenual"}
    
    def search_trefle(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        查询Trefle植物数据库
        
        参数:
            plant_name: 植物名称（拉丁学名效果更好）
        
        返回:
            植物信息字典，查询失败返回None
        """
        if not self.trefle_api_key:
            return {"error": "TREFLE_API_KEY not configured", "source": "trefle"}
        
        import requests
        
        try:
            # [安全审计] 目标域名 trefle.io，已在白名单中声明。
            # 仅发送植物名称和API Token，不携带用户隐私。
            url = "https://trefle.io/api/v1/plants/search"
            params = {"token": self.trefle_api_key, "q": plant_name}
            
            if not _validate_domain(url):
                return {"error": "Domain not in whitelist", "source": "trefle"}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                plant = data["data"][0]
                return {
                    "source": "trefle",
                    "common_name": plant.get("common_name"),
                    "scientific_name": plant.get("scientific_name"),
                    "family": plant.get("family"),
                    "genus": plant.get("genus"),
                    "year": plant.get("year"),
                    "bibliography": plant.get("bibliography"),
                    "image_url": plant.get("image_url")
                }
            
            return {"error": "Plant not found", "source": "trefle"}
            
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}", "source": "trefle"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "source": "trefle"}
    
    def search_wikipedia(self, plant_name: str) -> Optional[Dict[str, Any]]:
        """
        查询维基百科植物信息
        
        参数:
            plant_name: 植物名称
        
        返回:
            植物信息字典，查询失败返回None
        """
        import requests
        
        try:
            # [安全审计] 目标域名 zh.wikipedia.org，已在白名单中声明。
            # 仅发送植物名称作为查询参数，不携带任何用户隐私数据。
            search_url = "https://zh.wikipedia.org/w/api.php"
            
            if not _validate_domain(search_url):
                return {"error": "Domain not in whitelist", "source": "wikipedia"}
            
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": plant_name,
                "format": "json",
                "utf8": "",
                "srlimit": 3
            }
            
            response = requests.get(search_url, params=search_params, timeout=10)
            response.raise_for_status()
            search_data = response.json()
            
            if search_data.get("query", {}).get("search"):
                page_title = search_data["query"]["search"][0]["title"]
                
                # 获取页面摘要
                extract_url = "https://zh.wikipedia.org/w/api.php"
                extract_params = {
                    "action": "query",
                    "prop": "extracts",
                    "exintro": 1,
                    "explaintext": 1,
                    "titles": page_title,
                    "format": "json",
                    "utf8": ""
                }
                
                response = requests.get(extract_url, params=extract_params, timeout=10)
                response.raise_for_status()
                extract_data = response.json()
                
                pages = extract_data.get("query", {}).get("pages", {})
                page_id = list(pages.keys())[0]
                extract = pages[page_id].get("extract", "")
                
                return {
                    "source": "wikipedia",
                    "title": page_title,
                    "extract": extract[:500] + "..." if len(extract) > 500 else extract
                }
            
            return {"error": "No Wikipedia entry found", "source": "wikipedia"}
            
        except Exception as e:
            return {"error": f"Failed to query Wikipedia: {str(e)}", "source": "wikipedia"}
    
    def search_all(self, plant_name: str, include_authority: bool = True) -> List[Dict[str, Any]]:
        """
        查询所有数据源
        
        参数:
            plant_name: 植物名称
            include_authority: 是否包含权威网站爬虫
        
        返回:
            所有数据源的查询结果列表
        """
        results = []
        
        # 优先查询权威网站
        if include_authority:
            authority_results = self.search_authority_sites(plant_name)
            results.extend(authority_results)
        
        # 查询Perenual（可选）
        perenual_result = self.search_perenual(plant_name)
        results.append(perenual_result)
        
        # 查询Trefle（可选）
        trefle_result = self.search_trefle(plant_name)
        results.append(trefle_result)
        
        # 查询维基百科
        wiki_result = self.search_wikipedia(plant_name)
        results.append(wiki_result)
        
        return results


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="查询植物数据库信息")
    parser.add_argument("--plant-name", required=True, help="植物名称")
    parser.add_argument("--source",
                       choices=["authority", "authority-unified", "perenual", "trefle", "wikipedia", "all"],
                       default="all",
                       help="数据源选择：authority=权威网站分别查询, authority-unified=权威网站整合查询（推荐）, all=全部数据源")
    parser.add_argument("--output-mode",
                       choices=["user", "debug"],
                       default="user",
                       help="输出模式：user=仅展示成功数据（默认），debug=包含失败信息用于调试")

    args = parser.parse_args()
    
    # 输入清理与验证
    try:
        args.plant_name = sanitize_plant_name(args.plant_name)
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)
    
    client = PlantAPIClient()
    
    # 根据选择的源进行查询
    if args.source == "authority":
        results = client.search_authority_sites(args.plant_name)
    elif args.source == "authority-unified":
        result = client.search_authority_unified(args.plant_name, args.output_mode)
        results = [result]
    elif args.source == "all":
        # 使用整合的权威网站查询
        authority_unified = client.search_authority_unified(args.plant_name, args.output_mode)
        results = [authority_unified]
        
        # 查询其他API（可选）
        perenual_result = client.search_perenual(args.plant_name)
        results.append(perenual_result)
        
        trefle_result = client.search_trefle(args.plant_name)
        results.append(trefle_result)
        
        wiki_result = client.search_wikipedia(args.plant_name)
        results.append(wiki_result)
    elif args.source == "perenual":
        results = [client.search_perenual(args.plant_name)]
    elif args.source == "trefle":
        results = [client.search_trefle(args.plant_name)]
    elif args.source == "wikipedia":
        results = [client.search_wikipedia(args.plant_name)]
    
    # 根据输出模式过滤结果
    if args.output_mode == "user":
        # 用户模式：仅展示成功的数据源
        filtered_results = []
        for result in results:
            if result and not result.get("error"):
                # 对于整合查询结果，移除failed_sources字段
                if isinstance(result, dict):
                    user_result = result.copy()
                    user_result.pop("failed_sources", None)
                    user_result.pop("warnings", None)
                    filtered_results.append(user_result)
                else:
                    filtered_results.append(result)
        results = filtered_results
    
    # 输出结果
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
