package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum ReviewQuality {
    HARD("hard"),
    FUZZY("fuzzy"),
    REMEMBERED("remembered"),
    EASY("easy");

    private final String value;

    ReviewQuality(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static ReviewQuality fromValue(String value) {
        for (ReviewQuality quality : values()) {
            if (quality.value.equals(value)) {
                return quality;
            }
        }
        throw new IllegalArgumentException("Unsupported review quality: " + value);
    }
}
