# 洛克王国：世界精灵资料录入

主数据源建议使用 BWiki 洛克王国:手游WIKI：

- 精灵图鉴：https://wiki.biligame.com/rocom/精灵图鉴
- 示例详情页：https://wiki.biligame.com/rocom/迪莫

BWiki 页面目前覆盖你要录入的核心字段：编号、名称、属性、种族值、技能、进化链、分布/获得、特性、图片。RocoDex 可作为校验和补充来源。

## 字段

主表字段建议：

- `number`：编号，如 `001`
- `name`：精灵名称
- `attributes`：属性，JSON 数组，如 `["光"]`
- `stats_total`：种族值总和
- `hp`：生命
- `physical_attack`：物攻
- `magic_attack`：魔攻
- `physical_defense`：物防
- `magic_defense`：魔防
- `speed`：速度
- `skills`：精灵自带技能 JSON 数组
- `bloodline_skills`：改血脉可获得技能 JSON 数组
- `skill_stone_skills`：技能石可学技能 JSON 数组
- `evolution_chain`：进化链 JSON 或文本
- `obtain_method`：获得方式/分布
- `trait_name`：特性名称
- `trait_description`：特性说明
- `image_url`：立绘图片 URL
- `source_url`：资料来源页
- `source_updated_at`：来源页更新时间

## 目录

- `sources.md`：可用资料站和字段覆盖说明
- `schema.sql`：SQLite 建表语句
- `templates/spirits.csv`：CSV 录入模板
- `scripts/scrape_bwiki_rocom.py`：BWiki 采集脚本

## 采集示例

只采集图鉴索引：

```powershell
py -3 scripts/scrape_bwiki_rocom.py index --out data\roco_world_index.json
```

采集指定精灵：

```powershell
py -3 scripts/scrape_bwiki_rocom.py detail 迪莫 --out data\迪莫.json
```

从图鉴索引批量采集全部详情：

```powershell
py -3 scripts/scrape_bwiki_rocom.py all --out data\roco_world_spirits.json
```

注意：BWiki 内容采用 CC BY-NC-SA 4.0 授权，公开展示或二次分发时要标注来源。
