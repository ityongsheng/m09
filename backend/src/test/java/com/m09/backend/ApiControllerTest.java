package com.m09.backend;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {"spring.datasource.url=jdbc:sqlite:file:testdb?mode=memory&cache=shared", "m09.model.command="})
class ApiControllerTest {
    @Autowired MockMvc mvc;

    @Test void healthIsAvailable() throws Exception {
        mvc.perform(get("/api/health")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("ok"));
    }

    @Test void recordCanBeStoredAndListed() throws Exception {
        String body = "{\"fruit\":\"Orange\",\"temp\":4.2,\"humid\":85,\"light\":12,\"co2\":420}";
        mvc.perform(post("/api/records").contentType(MediaType.APPLICATION_JSON).content(body)).andExpect(status().isOk());
        mvc.perform(get("/api/records")).andExpect(status().isOk()).andExpect(jsonPath("$[0].fruit").value("Orange"));
    }

    @Test void predictionReportsMissingModelInsteadOfFakingResult() throws Exception {
        String body = "{\"record\":{\"fruit\":\"Orange\",\"temp\":4.2,\"humid\":85,\"light\":12,\"co2\":420}}";
        mvc.perform(post("/api/predict").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isServiceUnavailable()).andExpect(jsonPath("$.code").value("MODEL_UNAVAILABLE"));
    }
}
