#!/usr/bin/env bash
set -euo pipefail

# Create a project-local single-node HDFS configuration. Runtime data stays in
# .hadoop/, which is ignored by git. Pass --format explicitly for a new store.
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HADOOP_HOME="${HADOOP_HOME:-/opt/homebrew/opt/hadoop/libexec}"
JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
CONF_DIR="${HADOOP_CONF_DIR:-$PROJECT_ROOT/.hadoop/conf}"
RUNTIME_DIR="${M09_HADOOP_RUNTIME:-$PROJECT_ROOT/.hadoop/runtime}"

mkdir -p "$CONF_DIR" "$RUNTIME_DIR/name" "$RUNTIME_DIR/data" "$RUNTIME_DIR/tmp"
cat > "$CONF_DIR/core-site.xml" <<EOF
<?xml version="1.0"?>
<configuration>
  <property><name>fs.defaultFS</name><value>hdfs://localhost:9000</value></property>
  <property><name>hadoop.tmp.dir</name><value>file://$RUNTIME_DIR/tmp</value></property>
</configuration>
EOF
cat > "$CONF_DIR/hdfs-site.xml" <<EOF
<?xml version="1.0"?>
<configuration>
  <property><name>dfs.replication</name><value>1</value></property>
  <property><name>dfs.namenode.name.dir</name><value>file://$RUNTIME_DIR/name</value></property>
  <property><name>dfs.datanode.data.dir</name><value>file://$RUNTIME_DIR/data</value></property>
  <property><name>dfs.namenode.rpc-address</name><value>localhost:9000</value></property>
  <property><name>dfs.namenode.http-address</name><value>localhost:9870</value></property>
</configuration>
EOF
cat > "$CONF_DIR/hadoop-env.sh" <<EOF
export JAVA_HOME="$JAVA_HOME"
export HDFS_NAMENODE_USER="$(id -un)"
export HDFS_DATANODE_USER="$(id -un)"
export HDFS_SECONDARYNAMENODE_USER="$(id -un)"
EOF
cat > "$CONF_DIR/log4j.properties" <<'EOF'
log4j.rootLogger=INFO,console
log4j.appender.console=org.apache.log4j.ConsoleAppender
log4j.appender.console.target=System.err
log4j.appender.console.layout=org.apache.log4j.PatternLayout
log4j.appender.console.layout.ConversionPattern=%d{ISO8601} %-5p %c{1}: %m%n
EOF

if [[ "${1:-}" == "--format" ]]; then
  HADOOP_CONF_DIR="$CONF_DIR" JAVA_HOME="$JAVA_HOME" "$HADOOP_HOME/bin/hdfs" namenode -format -force -nonInteractive
fi

cat <<EOF
# Hadoop config ready: $CONF_DIR
export HADOOP_HOME="$HADOOP_HOME"
export HADOOP_CONF_DIR="$CONF_DIR"
export JAVA_HOME="$JAVA_HOME"
export PATH="$HADOOP_HOME/bin:$HADOOP_HOME/sbin:\$PATH"
EOF
