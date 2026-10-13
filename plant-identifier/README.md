# 🌿 plant-identifier · 智能植物识别

> 上传一张照片，识别野草野花绿植，判断危险性，并给出可执行的养护方案。

[![version](https://img.shields.io/badge/version-1.3.2-brightgreen)]()
[![python](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![license](https://img.shields.io/badge/license-MIT-lightgrey)]()

---

## 简介

**plant-identifier** 是一个植物识别与养护技能包（Skill）。它把「图像识别 + 危险植物检测 + 植物病理学 + 植物生理学 + 全球权威植物数据库查询」整合到一起，输出具体的植物名称、学名、科属、毒性判断和量化养护参数。

整合的权威数据源（7 个）：

| 数据源 | 机构 | 说明 |
| --- | --- | --- |
| 中国植物志 | 中国科学院植物研究所 | 国内权威植物学数据 |
| World Flora Online | 全球植物在线联盟 | 当前最权威的全球植物数据库 |
| IPNI | International Plant Names Index | 植物学名的权威来源 |
| Kew (POWO) | 英国皇家植物园 | 世界著名植物学研究机构 |
| Tropicos | 密苏里植物园 | 分类学数据库 |
| GBIF | 全球生物多样性信息机构 | 全球最大的生物多样性数据库 |
| USDA Plants | 美国农业部 | 北美植物官方数据 |

可选增强数据源：Perenual API、Trefle API（需自备密钥）。

---

## 能力范围

- **物种识别** —— 中文名、学名（拉丁名）、科属分类
- **危险性评估** —— 毒性 / 刺 / 过敏源 / 入侵性，输出危险等级
- **病理学诊断** —— 真菌、细菌、病毒病害与虫害、生理病害
- **生理学分析** —— 光合 / 呼吸 / 蒸腾作用、矿质营养、植物激素
- **养护方案** —— 光照、浇水、土壤、施肥、温湿度（含量化参数）
- **8 大专业维度** —— 分类学、形态学、物候学、生态学、地理分布、保护状况、经济用途、毒性
- **多方数据对比** —— 交叉验证并标注置信度与学术引用

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 直接对话使用

把本目录作为 Skill 加载后，上传植物照片并提问即可：

| 你想做什么 | 怎么问 |
| --- | --- |
| 识别植物 | 上传图片 + 「这是什么植物？」 |
| 检查是否有毒 | 上传图片 + 「有毒吗？」 |
| 获取养护建议 | 上传图片 + 「怎么养？」 |
| 诊断病害 | 上传图片 + 描述症状 |
| 季节养护 | 「月季夏天怎么养？」 |
| 权威数据查询 | 「帮我查一下银杏的权威数据」 |

### 3. 命令行查询权威数据库

```bash
# 整合查询全部权威数据源（推荐）
python3 scripts/plant_api_client.py --plant-name "月季" --source authority-unified --output-mode user

# 调试模式（额外输出失败数据源与警告信息）
python3 scripts/plant_api_client.py --plant-name "月季" --source authority-unified --output-mode debug

# 指定单一数据源
python3 scripts/plant_api_client.py --plant-name "Rosa chinensis" --source perenual
```

### 4. 可选：配置 API 密钥

```bash
export PERENUAL_API_KEY="your_key"   # https://perenual.com
export TREFLE_API_KEY="your_key"     # https://trefle.io
```

不配置也可正常使用，脚本会自动降级到内置植物常识库。

---

## 目录结构

```
plant-identifier/
├── SKILL.md                              # 技能主定义（frontmatter + 工作流）
├── README.md                             # 本文件
├── LICENSE                               # MIT
├── requirements.txt                      # Python 依赖
├── .gitignore
├── references/                           # 领域知识库
│   ├── care-operations.md                # 量化养护参数与操作步骤
│   ├── dangerous-plants.md               # 危险植物特征库
│   ├── data-sources.md                   # 数据来源分级、引用格式、置信度
│   ├── plant-care-diagnostics.md         # 问题诊断与解决方案
│   ├── plant-care-guide.md               # 基础养护要点
│   ├── plant-pathology.md                # 病害 / 虫害识别与防治
│   ├── plant-physiology.md               # 植物生理学原理
│   ├── plant-taxonomy.md                 # 分类学与形态学基础
│   ├── seasonal-care-calendar.md         # 四季逐月养护日历
│   └── terminology-glossary.md           # 术语解释与通俗对照
└── scripts/
    └── plant_api_client.py               # 权威数据库整合查询客户端
```

---

## 安全与隐私

- 所有外发请求的目标域名均在脚本内 `TRUSTED_DOMAIN_WHITELIST` 中显式声明，白名单外的域名请求会被 `_validate_domain()` 拦截。
- 请求仅包含植物名称等公开查询参数，**不传输任何用户隐私、地理位置或设备信息**。
- 外部数据源不可达时，自动降级为内置植物常识库，核心功能不中断。
- 脚本不包含 `eval` / `exec` / `subprocess` / 文件写入等危险调用。

> ⚠️ 免责声明：本项目输出的植物学信息基于公开数据与常识生成，**不可替代专业医疗诊断或农业专家现场指导**。涉及食用、药用请务必谨慎。

---

## 版本历史

| 版本 | 变更 |
| --- | --- |
| 1.3.2 | 当前版本：整合 7 大权威数据源，新增病理学与生理学模块 |
| 1.2.x | 引入可信域名白名单与离线降级机制 |

---

## License

[MIT](LICENSE)
