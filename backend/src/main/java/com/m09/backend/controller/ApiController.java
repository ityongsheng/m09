package com.m09.backend.controller;

import com.m09.backend.model.PredictionRequest;
import com.m09.backend.model.PredictionResponse;
import com.m09.backend.model.SensorRecordRequest;
import com.m09.backend.repository.PredictionRepository;
import com.m09.backend.repository.RecordRepository;
import com.m09.backend.service.ModelRunner;
import com.m09.backend.service.PredictionService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class ApiController {
    private final RecordRepository records;
    private final PredictionRepository predictions;
    private final PredictionService predictionService;
    public ApiController(RecordRepository records, PredictionRepository predictions, PredictionService predictionService) {
        this.records = records; this.predictions = predictions; this.predictionService = predictionService;
    }

    @GetMapping("/health")
    public Map<String,Object> health() { return Map.of("status", "ok", "service", "m09-backend"); }

    @GetMapping("/records")
    public List<Map<String,Object>> records(@RequestParam(defaultValue="100") int limit) { return records.list(Math.min(Math.max(limit,1),1000)); }

    @PostMapping("/records")
    public Map<String,Object> addRecord(@Valid @RequestBody SensorRecordRequest request) {
        return Map.of("id", records.insert(request), "status", "stored");
    }

    @PostMapping("/predict")
    public PredictionResponse predict(@Valid @RequestBody PredictionRequest request) { return predictionService.predict(request.record()); }

    @GetMapping("/predictions")
    public List<Map<String,Object>> predictions(@RequestParam(defaultValue="100") int limit) { return predictions.listPredictions(Math.min(Math.max(limit,1),1000)); }

    @GetMapping("/alerts")
    public List<Map<String,Object>> alerts(@RequestParam(defaultValue="100") int limit) { return predictions.listAlerts(Math.min(Math.max(limit,1),1000)); }

    @GetMapping("/experiments")
    public List<Map<String,Object>> experiments(@RequestParam(defaultValue="100") int limit) { return predictions.listExperiments(Math.min(Math.max(limit,1),1000)); }
}
