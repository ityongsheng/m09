package com.m09.backend.model;

import java.time.Instant;

public record ApiError(String code, String message, Instant timestamp) {}
