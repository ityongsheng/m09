package com.m09.backend.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record SensorRecordRequest(
        @NotBlank String fruit,
        @NotNull Double temp,
        @NotNull Double humid,
        @NotNull Double light,
        @NotNull Double co2,
        String source) {}
