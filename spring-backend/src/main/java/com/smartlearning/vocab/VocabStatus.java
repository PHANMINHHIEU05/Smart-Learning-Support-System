package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum VocabStatus {
    NOT_STARTED("not_started"),
    LEARNING("learning"),
    FUZZY("fuzzy"),
    REMEMBERED("remembered"),
    MASTERED("mastered"),
    ARCHIVED("archived");

    private final String value;

    VocabStatus(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static VocabStatus fromValue(String value) {
        String normalized = value == null ? "" : value.trim();
        for (VocabStatus status : values()) {
            if (status.value.equalsIgnoreCase(normalized) || status.name().equalsIgnoreCase(normalized)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unsupported vocab status: " + value);
    }
}
