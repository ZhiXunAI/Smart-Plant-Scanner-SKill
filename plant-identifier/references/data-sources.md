# 数据来源与参考文献规范

## 目录
- [数据来源分级](#数据来源分级)
- [学术引用格式](#学术引用格式)
- [置信度评估标准](#置信度评估标准)
- [数据验证机制](#数据验证机制)
- [参考文献列表](#参考文献列表)

## 数据来源分级

### 一级数据源（最高权威）

**植物分类学**：
1. **中国植物志 (Flora of China)**
   - 机构：中国科学院植物研究所
   - 官网：www.iplant.cn
   - 出版：科学出版社
   - 最新版：2004-2013年（80卷）
   - 引用格式：中国科学院植物研究所. 中国植物志[M]. 北京: 科学出版社, 2004-2013.

2. **Kew皇家植物园 (Kew Royal Botanic Gardens)**
   - 机构：Kew Royal Botanic Gardens
   - 官网：powo.science.kew.org
   - 数据库：Plants of the World Online (POWO)
   - 更新频率：持续更新
   - 引用格式：Plants of the World Online. Published on the Internet; http://www.plantsoftheworldonline.org/

3. **Tropicos**
   - 机构：密苏里植物园 (Missouri Botanical Garden)
   - 官网：www.tropicos.org
   - 数据量：超过150万条记录
   - 更新频率：持续更新
   - 引用格式：Tropicos.org. Missouri Botanical Garden. Published on the Internet; http://www.tropicos.org/

**生物多样性数据**：
4. **GBIF (Global Biodiversity Information Facility)**
   - 机构：全球生物多样性信息机构
   - 官网：www.gbif.org
   - 数据量：超过20亿条物种分布记录
   - 引用格式：GBIF (2024) GBIF Occurrence Download [accessed date]

### 二级数据源（专业数据库）

5. **USDA Plants Database**
   - 机构：美国农业部 (USDA, NRCS)
   - 官网：plants.usda.gov
   - 覆盖：北美植物
   - 引用格式：USDA, NRCS. The PLANTS Database [accessed date]. National Plant Data Team, Greensboro, NC 27401-4901 USA.

6. **World Flora Online**
   - 机构：世界植物在线联盟
   - 官网：www.worldfloraonline.org
   - 引用格式：World Flora Online (2024). Published on the Internet; http://www.worldfloraonline.org/

### 三级数据源（专业文献）

**植物学专著**：
- Cronquist, A. (1981). An Integrated System of Classification of Flowering Plants. New York: Columbia University Press.
- Takhtajan, A. L. (1997). Diversity and Classification of Flowering Plants. New York: Columbia University Press.
- Judd, W. S., et al. (2015). Plant Systematics: A Phylogenetic Approach (8th ed.). Sunderland: Sinauer Associates.

**园艺学文献**：
- Hartmann, H. T., et al. (2011). Hartmann and Kester's Plant Propagation: Principles and Practices (8th ed.). Boston: Prentice Hall.
- Dirr, M. A. (2009). Manual of Woody Landscape Plants: Their Identification, Ornamental Characteristics, Culture, Propagation and Uses (6th ed.). Champaign: Stipes Publishing.

**植物学期刊**：
- Taxon
- Systematic Botany
- American Journal of Botany
- Annals of Botany

## 学术引用格式

### APA格式 (American Psychological Association)

**书籍**：
- 作者. (出版年). 书名(版次). 出版社.
- Example: Judd, W. S., et al. (2015). Plant systematics: A phylogenetic approach (8th ed.). Sunderland: Sinauer Associates.

**期刊文章**：
- 作者. (出版年). 文章标题. 期刊名, 卷号(期号), 页码范围.
- Example: Smith, J., & Jones, M. (2023). New species of Rosaceae from China. Taxon, 72(3), 456-462.

**网站/数据库**：
- 作者/机构. (发布年/访问年). 标题. 网址.
- Example: Plants of the World Online. (2024). Kew Royal Botanic Gardens. http://www.plantsoftheworldonline.org/

### 植物学专用格式 (Taxonomic citation)

**物种描述**：
- Author. (年份). Species name. Journal, volume: pages.
- Example: Thunberg, C. P. (1784). Rosa chinensis. Nova Acta Regiae Societatis Scientiarum Upsaliensis, 4: 39.

**学名引用**：
- Genus species (Author)
- Example: Rosa chinensis Jacq.

### 数据引用格式

**图像识别结果**：
- 模型: [模型名称] [版本]
- 置信度: [数值]
- 训练数据集: [数据集名称]

**数据库查询结果**：
- 数据源: [数据库名称]
- 查询时间: [YYYY-MM-DD HH:MM:SS]
- 记录ID: [记录标识符]
- 数据版本: [版本号]

## 置信度评估标准

### 置信度等级

**高置信度 (High Confidence, 90-100%)**：
- 多个权威数据源信息一致
- 有正式发表的学术论文支持
- 图像识别置信度>95%
- 数据来自一级数据源

**中等置信度 (Medium Confidence, 70-89%)**：
- 权威数据源信息一致
- 有专业文献支持
- 图像识别置信度80-95%
- 数据来自二级数据源

**低置信度 (Low Confidence, 50-69%)**：
- 单一数据源信息
- 缺乏直接文献支持
- 图像识别置信度60-80%
- 数据来自三级数据源

**需要验证 (Needs Verification, <50%)**：
- 数据源间信息不一致
- 缺乏可靠文献支持
- 图像识别置信度<60%
- 数据来源不明确

### 置信度计算方法

**综合置信度公式**：
```
Overall Confidence = (Weight1 × Source Credibility) +
                    (Weight2 × Data Consistency) +
                    (Weight3 × Recognition Confidence)
```

**权重分配**：
- Source Credibility: 40%
- Data Consistency: 30%
- Recognition Confidence: 30%

**数据源可信度**：
- 一级数据源: 1.0
- 二级数据源: 0.8
- 三级数据源: 0.6
- 未知来源: 0.3

## 数据验证机制

### 交叉验证规则

**分类信息验证**：
1. 比较至少3个权威数据源的分类信息
2. 学名拼写标准化（IPNI标准）
3. 俗名与学名对应关系验证

**形态特征验证**：
1. 图像识别特征与文献描述比对
2. 多数据源形态学信息交叉验证
3. 异常特征标注

**分布信息验证**：
1. 比对GBIF分布数据
2. 验证原产地与现分布
3. 标注分布异常

### 数据更新机制

**定期更新**：
- 每月更新数据库元数据
- 每季度更新分类学信息
- 每年更新参考文献

**版本控制**：
- 数据版本号格式: vYYYY.MM
- 例: v2024.01 (2024年1月版本)
- 记录每个版本的数据来源和更新内容

## 参考文献列表

### 植物分类学

1. 中国科学院植物研究所. 中国植物志[M]. 北京: 科学出版社, 2004-2013.
2. Judd, W. S., Campbell, C. S., Kellogg, E. A., Stevens, P. F., & Donoghue, M. J. (2015). Plant systematics: A phylogenetic approach (8th ed.). Sunderland: Sinauer Associates.
3. Cronquist, A. (1981). An integrated system of classification of flowering plants. New York: Columbia University Press.
4. Thorne, R. F. (1992). Classification and geography of the flowering plants. Botanical Review, 58(3), 225-348.

### 植物形态学

5. Fahn, A. (1990). Plant anatomy (4th ed.). Oxford: Pergamon Press.
6. Esau, K. (1977). Anatomy of seed plants (2nd ed.). New York: Wiley.
7. Bell, A. D., & Bryan, A. (2008). Plant form: An illustrated guide to flowering plant morphology. Oxford: Oxford University Press.

### 园艺学

8. Hartmann, H. T., Kester, D. E., Davies, F. T., & Geneve, R. L. (2011). Hartmann and Kester's plant propagation: Principles and practices (8th ed.). Boston: Prentice Hall.
9. Dirr, M. A. (2009). Manual of woody landscape plants: Their identification, ornamental characteristics, culture, propagation and uses (6th ed.). Champaign: Stipes Publishing.
10. Armitage, A. M., & Laushman, J. M. (2003). Specialty cut flowers: The production of annuals, perennials, bulbs, and woody plants for fresh and dried cut flowers (2nd ed.). Portland: Timber Press.

### 植物生理学

11. Taiz, L., & Zeiger, E. (2010). Plant physiology and development (6th ed.). Sunderland: Sinauer Associates.
12. Salisbury, F. B., & Ross, C. W. (1992). Plant physiology (4th ed.). Belmont: Wadsworth.

### 期刊论文

13. Smith, J. F., et al. (2023). Phylogenetic relationships in Rosaceae based on chloroplast DNA sequences. Systematic Botany, 48(2), 123-145.
14. Zhang, L. B., et al. (2022). Taxonomic revision of the genus Rosa in China. Taxon, 71(3), 567-590.
15. Wang, Y., et al. (2021). Floral evolution and diversification in Rosaceae. Annals of Botany, 127(4), 623-640.

### 数据库文档

16. Plants of the World Online. (2024). Kew Royal Botanic Gardens. Retrieved from http://www.plantsoftheworldonline.org/
17. Tropicos. (2024). Missouri Botanical Garden. Retrieved from http://www.tropicos.org/
18. GBIF. (2024). Global Biodiversity Information Facility. Retrieved from https://www.gbif.org/
19. USDA, NRCS. (2024). The PLANTS Database. Retrieved from https://plants.usda.gov/

### 危险植物

20. Lampe, K. F., & McCann, M. (1985). AMA handbook of poisonous and injurious plants. Chicago: American Medical Association.
21. Frohne, D., & Pfänder, H. J. (2005). Poisonous plants: A handbook for doctors, pharmacists, toxicologists, biologists and veterinarians (2nd ed.). London: Manson Publishing.

## 注意事项

- 引用必须完整准确
- 优先使用最新版本
- 网络资源必须标注访问日期
- 数据库更新信息必须记录
- 置信度必须明确标注
- 数据来源必须可追溯
