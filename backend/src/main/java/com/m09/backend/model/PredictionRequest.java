package com.m09.backend.model;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;

public record PredictionRequest(@Valid @NotNull SensorRecordRequest record) {}
