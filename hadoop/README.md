# Hadoop/HDFS 数据链路

`hdfs_ingest.sh` 使用运行中的 HDFS 完成真实数据上传、下载、清洗、报告和结果回传：

```bash
HDFS_ROOT=/m09/cold-storage hadoop/hdfs_ingest.sh
```

脚本需要本机已启动 Hadoop 伪分布式环境，或在 Hadoop 容器内执行。没有 `hdfs` 命令时会返回明确的阻断信息，不会把本地清洗伪装成 HDFS 验证。运行日志保存在 `evidence/hadoop/run/`，该目录属于本地证据，不提交运行时数据库或凭据。

本机实机验证使用 Hadoop 3.5.0、Java 17 和项目内 `.hadoop/conf` 单节点配置，NameNode 为 `hdfs://localhost:9000`，验证结果见 `evidence/delivery/hadoop-real-run.json`。

重新配置本机环境：

```bash
eval "$(hadoop/setup_local_hdfs.sh)"
hadoop/setup_local_hdfs.sh --format   # 仅新建本地 HDFS 存储时执行
export HDFS_BIN="$HADOOP_HOME/bin/hdfs"
hdfs --daemon start namenode
hdfs --daemon start datanode
HDFS_ROOT=/m09/cold-storage hadoop/hdfs_ingest.sh
```
