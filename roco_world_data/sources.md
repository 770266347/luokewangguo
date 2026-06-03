# 数据源

## 主源：BWiki 洛克王国:手游WIKI

- 精灵图鉴：https://wiki.biligame.com/rocom/精灵图鉴
- 示例详情页：https://wiki.biligame.com/rocom/迪莫
- 官网链接：https://rocom.qq.com

适合字段：

- 编号
- 名称
- 属性
- 立绘图片
- 种族值：总和、生命、物攻、魔攻、物防、魔防、速度
- 精灵分布/获得方式
- 特性名称和说明
- 进化链
- 技能列表

页面标注协议为 CC BY-NC-SA 4.0，录入时建议保存 `source_url` 和 `source_updated_at`。

## 补充源：RocoDex

- https://rocodex.org/zh

适合补充校验：

- 精灵图鉴
- 技能库
- 道具
- 属性克制
- 蛋组

## 字段优先级

1. BWiki 详情页为主，以页面上显示的数据为准。
2. BWiki 缺失或字段疑似异常时，用 RocoDex 做人工校验。
3. 图片优先用 BWiki 详情页的立绘图 URL。
