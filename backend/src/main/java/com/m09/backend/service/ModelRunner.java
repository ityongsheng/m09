package com.m09.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.m09.backend.model.ModelPrediction;
import com.m09.backend.model.SensorRecordRequest;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class ModelRunner {
    private final ObjectMapper mapper;
    private final String command;
    private final long timeoutMs;

    public ModelRunner(ObjectMapper mapper,
                       @Value("${m09.model.command:}") String command,
                       @Value("${m09.model.timeout-ms:15000}") long timeoutMs) {
        this.mapper = mapper; this.command = command == null ? "" : command.trim(); this.timeoutMs = timeoutMs;
    }

    public ModelPrediction predict(SensorRecordRequest input) {
        if (command.isBlank()) {
            throw new ModelUnavailableException("模型运行命令未配置，请设置 M09_MODEL_COMMAND");
        }
        try {
            // The setting is a single executable path. ProcessBuilder avoids shell
            // interpolation and therefore supports Windows paths containing spaces.
            Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
            String request = mapper.writeValueAsString(input);
            process.getOutputStream().write((request + "\n").getBytes(StandardCharsets.UTF_8));
            process.getOutputStream().close();
            if (!process.waitFor(timeoutMs, TimeUnit.MILLISECONDS)) {
                process.destroyForcibly();
                throw new ModelUnavailableException("模型运行超时");
            }
            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8).trim();
            if (process.exitValue() != 0 || output.isBlank()) {
                throw new ModelUnavailableException("模型进程失败：" + output);
            }
            return mapper.readValue(output, ModelPrediction.class);
        } catch (IOException e) {
            throw new ModelUnavailableException("无法启动模型运行命令：" + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ModelUnavailableException("模型调用被中断", e);
        }
    }

    public static class ModelUnavailableException extends RuntimeException {
        public ModelUnavailableException(String message) { super(message); }
        public ModelUnavailableException(String message, Throwable cause) { super(message, cause); }
    }
}
