package com.m09.backend.model;

public record ModelPrediction(String label, double riskProbability, String modelVersion, String metricsJson) {}
