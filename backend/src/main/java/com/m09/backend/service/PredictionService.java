package com.m09.backend.service;

import com.m09.backend.model.ModelPrediction;
import com.m09.backend.model.PredictionResponse;
import com.m09.backend.model.SensorRecordRequest;
import com.m09.backend.repository.PredictionRepository;
import com.m09.backend.repository.RecordRepository;
import org.springframework.stereotype.Service;

@Service
public class PredictionService {
    private final RecordRepository records;
    private final PredictionRepository predictions;
    private final ModelRunner modelRunner;

    public PredictionService(RecordRepository records, PredictionRepository predictions, ModelRunner modelRunner) {
        this.records = records; this.predictions = predictions; this.modelRunner = modelRunner;
    }

    public PredictionResponse predict(SensorRecordRequest request) {
        long recordId = records.insert(request);
        ModelPrediction model = modelRunner.predict(request);
        long predictionId = predictions.insert(recordId, model);
        boolean bad = "Bad".equalsIgnoreCase(model.label()) || model.riskProbability() >= 0.5;
        String level = bad ? "HIGH" : "NORMAL";
        String message = bad ? "该传感器记录被模型判定为高风险" : "该传感器记录暂未发现高风险";
        if (bad) predictions.insertAlert(predictionId, level, message);
        return new PredictionResponse(predictionId, recordId, model.label(), model.riskProbability(), model.modelVersion(), level, message);
    }
}
