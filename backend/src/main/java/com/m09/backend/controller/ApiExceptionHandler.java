package com.m09.backend.controller;

import com.m09.backend.model.ApiError;
import com.m09.backend.service.ModelRunner;
import java.time.Instant;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(ModelRunner.ModelUnavailableException.class)
    @ResponseStatus(HttpStatus.SERVICE_UNAVAILABLE)
    ApiError modelUnavailable(ModelRunner.ModelUnavailableException e) { return new ApiError("MODEL_UNAVAILABLE", e.getMessage(), Instant.now()); }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    ApiError invalid(MethodArgumentNotValidException e) { return new ApiError("INVALID_INPUT", "请求字段缺失或格式不正确", Instant.now()); }
}
