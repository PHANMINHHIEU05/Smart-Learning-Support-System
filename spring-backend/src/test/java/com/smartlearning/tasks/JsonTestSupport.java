package com.smartlearning.tasks;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;

public final class JsonTestSupport {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private JsonTestSupport() {
    }

    public static String extractString(String json, String fieldName) throws IOException {
        JsonNode value = OBJECT_MAPPER.readTree(json).get(fieldName);
        if (value == null || value.isNull()) {
            throw new IllegalArgumentException("Missing JSON field: " + fieldName);
        }
        return value.asText();
    }
}
