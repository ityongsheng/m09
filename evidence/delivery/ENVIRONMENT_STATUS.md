# m09 环境与交付状态

## 已验证

- macOS 本机 Python 模型与 JSON 运行器测试：5/5 通过（使用模型虚拟环境）。
- 清洗管线：真实 Mendeley CSV 输入 10,995 条，输出 10,995 条。
- Spring Boot + SQLite Maven 测试：3 项通过。
- 静态前端 `node --check backend/src/main/resources/static/app.js` 通过。
- 模型 JSON stdin/stdout 合约测试：使用真实清洗数据训练临时模型后通过。
- Spring Boot 本机联调：`/api/health`、静态首页、记录写入、预测、预测历史和高风险预警接口均返回预期结果；SQLite 数据写入成功。
- Hadoop 3.5.0 单节点伪分布式 HDFS 实机运行：NameNode/DataNode 启动，1 个 DataNode 在线，原始 CSV 上传、回读、清洗和结果回传成功；回读原始文件 SHA-256 与本地一致。
- GitHub Actions Windows x64 PyInstaller 模型 EXE：构建、原生 smoke 输入输出和 PE32+ x86-64 检查通过，已发布模型运行器 Release 资产。

## 尚未验证

- 尚未在 Windows 10/11 x64 原生环境验收全应用离线包；本次按要求不制作全应用 Windows x64 包。
- 尚未执行断网、中文空格路径和无预装依赖的 Windows 全应用验收。

## 交付前条件

1. 如后续需要全应用 Windows 包，再在 Windows x64 原生环境构建 Spring Boot JAR、启动入口和离线目录。
2. 当前模型 EXE 使用 `evidence/delivery/model-exe-windows.json` 中的 Release 资产。
