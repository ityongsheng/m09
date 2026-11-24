# m09 实施计划

## 课题
基于 Hadoop 与 XGBoost 的生鲜仓储传感器记录损耗预测系统的设计与实现。

## 数据与口径
- 数据源：Mendeley Data `czz68d9fwj/1`，DOI `10.17632/czz68d9fwj.1`，CC BY 4.0。
- 数据是冷库传感器记录表，不含时间戳；不将其描述为严格时序数据。
- 字段：`Fruit`、`Temp`、`Humid`、`Light`、`CO2`、`Class`；`Good=0`、`Bad=1`。
- 不使用仿真数据，不调用大模型 API。

## 技术路线
Python 数据清洗与模型实验；Hadoop/HDFS 负责可复现的数据处理验证；Spring Boot + SQLite 提供业务 API；静态 Web 页面提供记录查看、预测和预警展示。

## 验收边界
- 分类指标为主：Accuracy、Precision、Recall、F1、ROC-AUC。
- MSE、MAE、R² 作为概率输出的辅助指标，以兼容开题报告。
- Docker 仅用于开发和服务联调；最终提供 Windows 10/11 x64 离线 ZIP、`start.cmd`、`stop.cmd`、`launcher.json`。
- 所有论文结果、截图和测试数据必须来自真实运行记录。
