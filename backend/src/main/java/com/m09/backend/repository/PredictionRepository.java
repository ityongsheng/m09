package com.m09.backend.repository;

import com.m09.backend.model.ModelPrediction;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class PredictionRepository {
    private final JdbcTemplate jdbc;
    private final Clock clock;
    public PredictionRepository(JdbcTemplate jdbc, Clock clock) { this.jdbc = jdbc; this.clock = clock; }

    public long insert(long recordId, ModelPrediction p) {
        jdbc.update("INSERT INTO prediction_record(sensor_record_id,label,risk_probability,model_version,metrics_json,created_at) VALUES(?,?,?,?,?,?)",
                recordId, p.label(), p.riskProbability(), p.modelVersion(), p.metricsJson(), Instant.now(clock).toString());
        return jdbc.queryForObject("SELECT last_insert_rowid()", Long.class);
    }

    public long insertAlert(long predictionId, String level, String message) {
        jdbc.update("INSERT INTO alert_record(prediction_id,level,message,status,created_at) VALUES(?,?,?,?,?)",
                predictionId, level, message, "OPEN", Instant.now(clock).toString());
        return jdbc.queryForObject("SELECT last_insert_rowid()", Long.class);
    }

    public List<Map<String,Object>> listPredictions(int limit) {
        return jdbc.queryForList("SELECT id,sensor_record_id,label,risk_probability,model_version,metrics_json,created_at FROM prediction_record ORDER BY id DESC LIMIT ?", limit);
    }

    public List<Map<String,Object>> listAlerts(int limit) {
        return jdbc.queryForList("SELECT a.id,a.prediction_id,p.label,p.risk_probability,a.level AS alert_level,a.message AS alert_message,a.status,a.created_at "
                + "FROM alert_record a JOIN prediction_record p ON p.id=a.prediction_id "
                + "ORDER BY a.id DESC LIMIT ?", limit);
    }

    public List<Map<String,Object>> listExperiments(int limit) {
        return jdbc.queryForList("SELECT id,model_name,accuracy,precision_value,recall_value,f1,roc_auc,mse,mae,r2,config_json,created_at FROM experiment_metric ORDER BY id DESC LIMIT ?", limit);
    }
}
