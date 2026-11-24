package com.m09.backend.repository;

import com.m09.backend.model.SensorRecordRequest;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class RecordRepository {
    private final JdbcTemplate jdbc;
    private final Clock clock;

    public RecordRepository(JdbcTemplate jdbc, Clock clock) { this.jdbc = jdbc; this.clock = clock; }

    public long insert(SensorRecordRequest r) {
        String now = Instant.now(clock).toString();
        jdbc.update("INSERT INTO sensor_record(fruit,temp,humid,light,co2,source,created_at) VALUES (?,?,?,?,?,?,?)",
                r.fruit(), r.temp(), r.humid(), r.light(), r.co2(), r.source(), now);
        return jdbc.queryForObject("SELECT last_insert_rowid()", Long.class);
    }

    public List<Map<String,Object>> list(int limit) {
        return jdbc.queryForList("SELECT id,fruit,temp,humid,light,co2,source,created_at FROM sensor_record ORDER BY id DESC LIMIT ?", limit);
    }
}
