package com.m09.backend.model;

public record PredictionResponse(long predictionId, long sensorRecordId, String label,
                                 double riskProbability, String modelVersion,
                                 String alertLevel, String alertMessage) {}
